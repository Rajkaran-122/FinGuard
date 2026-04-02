"""
Record Repository
==================
All database queries for financial records including aggregations.
All queries automatically exclude soft-deleted records.
"""

from datetime import date, datetime, timezone
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.models.record import FinancialRecord, RecordType


def _active_records(db: Session):
    """Base query filtering out soft-deleted records."""
    return db.query(FinancialRecord).filter(FinancialRecord.deleted_at.is_(None))


def create_record(
    db: Session, amount: Decimal, record_type: str, category: str,
    record_date: date, created_by: str, notes: Optional[str] = None
) -> FinancialRecord:
    """Create a new financial record."""
    record = FinancialRecord(
        amount=amount,
        type=RecordType(record_type),
        category=category,
        date=record_date,
        notes=notes,
        created_by=created_by,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_record_by_id(db: Session, record_id: str) -> Optional[FinancialRecord]:
    """Fetch a single active record by ID."""
    return _active_records(db).filter(FinancialRecord.id == record_id).first()


def get_records(
    db: Session,
    record_type: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
) -> Tuple[List[FinancialRecord], int]:
    """
    Fetch records with optional filters and pagination.
    Returns (records, total_count).
    """
    query = _active_records(db)

    if record_type:
        query = query.filter(FinancialRecord.type == RecordType(record_type))
    if category:
        query = query.filter(FinancialRecord.category == category)
    if date_from:
        query = query.filter(FinancialRecord.date >= date_from)
    if date_to:
        query = query.filter(FinancialRecord.date <= date_to)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (FinancialRecord.notes.ilike(search_pattern)) |
            (FinancialRecord.category.ilike(search_pattern))
        )

    total = query.count()
    records = (
        query.order_by(FinancialRecord.date.desc(), FinancialRecord.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return records, total


def update_record(db: Session, record: FinancialRecord, **kwargs) -> FinancialRecord:
    """Update record fields from keyword arguments."""
    for key, value in kwargs.items():
        if value is not None:
            if key == "type":
                setattr(record, key, RecordType(value))
            else:
                setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def soft_delete_record(db: Session, record: FinancialRecord) -> FinancialRecord:
    """Soft-delete a record by setting deleted_at timestamp."""
    record.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record


# --- Aggregation Queries ---

def get_summary_totals(
    db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None
) -> dict:
    """Calculate total income, total expenses, and net balance."""
    query = db.query(
        func.coalesce(
            func.sum(case((FinancialRecord.type == RecordType.INCOME, FinancialRecord.amount))),
            0
        ).label("total_income"),
        func.coalesce(
            func.sum(case((FinancialRecord.type == RecordType.EXPENSE, FinancialRecord.amount))),
            0
        ).label("total_expenses"),
        func.count(FinancialRecord.id).label("record_count"),
    ).filter(FinancialRecord.deleted_at.is_(None))

    if date_from:
        query = query.filter(FinancialRecord.date >= date_from)
    if date_to:
        query = query.filter(FinancialRecord.date <= date_to)

    result = query.first()
    total_income = float(result.total_income or 0)
    total_expenses = float(result.total_expenses or 0)

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_balance": total_income - total_expenses,
        "record_count": result.record_count,
    }


def get_category_breakdown(
    db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None
) -> List[dict]:
    """Get category-wise totals grouped by type."""
    query = db.query(
        FinancialRecord.category,
        FinancialRecord.type,
        func.sum(FinancialRecord.amount).label("total"),
        func.count(FinancialRecord.id).label("count"),
    ).filter(
        FinancialRecord.deleted_at.is_(None)
    ).group_by(
        FinancialRecord.category, FinancialRecord.type
    )

    if date_from:
        query = query.filter(FinancialRecord.date >= date_from)
    if date_to:
        query = query.filter(FinancialRecord.date <= date_to)

    results = query.all()
    return [
        {
            "category": r.category,
            "type": r.type.value if hasattr(r.type, 'value') else r.type,
            "total": float(r.total),
            "count": r.count,
        }
        for r in results
    ]


def get_monthly_trends(
    db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None
) -> List[dict]:
    """
    Get monthly aggregated trends using SQLite's strftime.
    Groups by YYYY-MM and returns income, expense, net per period.
    """
    period_expr = func.strftime("%Y-%m", FinancialRecord.date)

    query = db.query(
        period_expr.label("period"),
        func.coalesce(
            func.sum(case((FinancialRecord.type == RecordType.INCOME, FinancialRecord.amount))),
            0
        ).label("income"),
        func.coalesce(
            func.sum(case((FinancialRecord.type == RecordType.EXPENSE, FinancialRecord.amount))),
            0
        ).label("expense"),
    ).filter(
        FinancialRecord.deleted_at.is_(None)
    ).group_by(period_expr).order_by(period_expr)

    if date_from:
        query = query.filter(FinancialRecord.date >= date_from)
    if date_to:
        query = query.filter(FinancialRecord.date <= date_to)

    results = query.all()
    return [
        {
            "period": r.period,
            "income": float(r.income),
            "expense": float(r.expense),
            "net": float(r.income) - float(r.expense),
        }
        for r in results
    ]


def get_recent_records(db: Session, limit: int = 10) -> Tuple[List[FinancialRecord], int]:
    """Get the N most recent financial records."""
    query = _active_records(db)
    total = query.count()
    records = (
        query.order_by(FinancialRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return records, total
