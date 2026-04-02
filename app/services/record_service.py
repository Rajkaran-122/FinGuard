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
from app.core.cache import cache_service


def create_record(
    db: Session, amount: Decimal, record_type: str, category: str,
    record_date: date, created_by: str, notes: Optional[str] = None
):
    """Create a new financial record triggering Cache Invalidation event hooks."""
    record = record_repository.create_record(
        db, amount, record_type, category, record_date, created_by, notes
    )
    cache_service.invalidate_prefix("dashboard_")
    return record


def list_records(
    db: Session, record_type: Optional[str] = None, category: Optional[str] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    search: Optional[str] = None, cursor: Optional[str] = None, page: int = 1, limit: int = 50,
):
    """List records with cursors/pagination."""
    records, total, next_cursor = record_repository.get_records(
        db, record_type, category, date_from, date_to, search, cursor, page, limit
    )
    return {"records": records, "total": total, "next_cursor": next_cursor, "page": page, "limit": limit}


def get_record(db: Session, record_id: str):
    """Get a single record by ID."""
    record = record_repository.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record


def update_record(db: Session, record_id: str, **kwargs):
    """Full or partial update triggering Cache Invalidation event hooks."""
    record = record_repository.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    updated = record_repository.update_record(db, record, **kwargs)
    cache_service.invalidate_prefix("dashboard_")
    return updated


def delete_record(db: Session, record_id: str):
    """Soft-delete a record triggering Cache Invalidation event hooks."""
    record = record_repository.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    record_repository.soft_delete_record(db, record)
    cache_service.invalidate_prefix("dashboard_")
    return {"detail": "Record deleted successfully"}
