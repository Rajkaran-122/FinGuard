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
from app.core.cache import cache_service


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
    
    # Invalidate dashboard cache aggressively on writes
    cache_service.invalidate_prefix("dashboard_")
    
    return record


def get_record_by_id(db: Session, record_id: str) -> Optional[FinancialRecord]:
    """Fetch a single active record by ID."""
    return _active_records(db).filter(FinancialRecord.id == record_id).first()


import json

def _log_audit(db: Session, record_id: str, action: str, old_dict: dict, new_dict: dict):
    from app.models.record import FinancialRecordAudit
    db.add(FinancialRecordAudit(
        record_id=record_id,
        action_type=action,
        old_state=json.dumps(old_dict, default=str),
        new_state=json.dumps(new_dict, default=str)
    ))

def get_records(
    db: Session,
    record_type: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    cursor: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
) -> Tuple[List[FinancialRecord], int, Optional[str]]:
    """Return records, total count, and next cursor."""
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
    
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
            query = query.filter(FinancialRecord.created_at < cursor_dt)
        except ValueError:
            pass

    total = query.count()
    records = (
        query.order_by(FinancialRecord.created_at.desc())
        .limit(limit)
        .all()
    ) if cursor else (
        query.order_by(FinancialRecord.date.desc(), FinancialRecord.created_at.desc())
        .offset((page - 1) * limit).limit(limit).all()
    )
    
    next_cursor = records[-1].created_at.isoformat() if len(records) == limit else None
    return records, total, next_cursor


def update_record(db: Session, record: FinancialRecord, **kwargs) -> FinancialRecord:
    """Update record with Immutable Audit Logs."""
    old_state = {c.name: getattr(record, c.name) for c in record.__table__.columns}
    for key, value in kwargs.items():
        if value is not None:
            if key == "type":
                setattr(record, key, RecordType(value))
            else:
                setattr(record, key, value)
                
    new_state = {c.name: getattr(record, c.name) for c in record.__table__.columns}
    _log_audit(db, record.id, "UPDATE", old_state, new_state)
    
    db.commit()
    db.refresh(record)
    
    cache_service.invalidate_prefix("dashboard_")
    
    return record


def soft_delete_record(db: Session, record: FinancialRecord) -> FinancialRecord:
    """Soft-delete triggers an Immutable Audit trail."""
    old_state = {c.name: getattr(record, c.name) for c in record.__table__.columns}
    record.deleted_at = datetime.now(timezone.utc)
    new_state = {c.name: getattr(record, c.name) for c in record.__table__.columns}
    
    _log_audit(db, record.id, "SOFT_DELETE", old_state, new_state)
    
    db.commit()
    db.refresh(record)
    
    cache_service.invalidate_prefix("dashboard_")
    
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
