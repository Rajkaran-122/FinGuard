"""
Record Service
===============
Financial record business rules.
"""

from datetime import date
from typing import Optional
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories import record_repository


def create_record(
    db: Session, amount: Decimal, record_type: str, category: str,
    record_date: date, created_by: str, notes: Optional[str] = None
):
    """Create a new financial record."""
    return record_repository.create_record(
        db, amount, record_type, category, record_date, created_by, notes
    )


def list_records(
    db: Session, record_type: Optional[str] = None, category: Optional[str] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    search: Optional[str] = None, page: int = 1, limit: int = 50,
):
    """List records with filters and pagination."""
    records, total = record_repository.get_records(
        db, record_type, category, date_from, date_to, search, page, limit
    )
    return {"records": records, "total": total, "page": page, "limit": limit}


def get_record(db: Session, record_id: str):
    """Get a single record by ID."""
    record = record_repository.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record


def update_record(db: Session, record_id: str, **kwargs):
    """Full or partial update of a financial record."""
    record = record_repository.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record_repository.update_record(db, record, **kwargs)


def delete_record(db: Session, record_id: str):
    """Soft-delete a financial record."""
    record = record_repository.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    record_repository.soft_delete_record(db, record)
    return {"detail": "Record deleted successfully"}
