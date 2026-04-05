"""
Record Service
===============
Financial record business rules with ownership-scoped data access.

SECURITY DESIGN: Every operation receives the current_user object.
The service determines the effective user_id scope:
  - Admin users (with 'records:write' permission) -> user_id=None (see all)
  - All other users -> user_id=current_user.id (see only own data)

This ensures IDOR protection at the service boundary before any
database query is executed.
"""

from datetime import date
from typing import Optional
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories import record_repository
from app.core.cache import cache_service
from app.models.user import User


def _get_scope(user: User) -> Optional[str]:
    """
    Determine data scope based on user permissions.

    Returns None for admin-level users (no ownership filter),
    or the user's ID to scope queries to their own records.

    This is the SINGLE function that controls multi-tenancy behavior.
    Adding a new role (e.g., 'Auditor') only requires granting them
    the appropriate permissions — zero code changes needed.
    """
    user_perms = user.permissions or []
    if "records:write" in user_perms or "users:manage" in user_perms:
        return None  # Admin-level: see all records
    return user.id  # Scoped: see only own records


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
    db: Session, current_user: User,
    record_type: Optional[str] = None, category: Optional[str] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    search: Optional[str] = None, cursor: Optional[str] = None,
    page: int = 1, limit: int = 50,
):
    """List records scoped to user ownership."""
    scope = _get_scope(current_user)
    records, total, next_cursor = record_repository.get_records(
        db, record_type, category, date_from, date_to, search, cursor, page, limit,
        user_id=scope,
    )
    return {"records": records, "total": total, "next_cursor": next_cursor, "page": page, "limit": limit}


def get_record(db: Session, record_id: str, current_user: User):
    """
    Get a single record by ID with ownership enforcement.

    SECURITY: Returns 404 (not 403) when record exists but belongs to
    another user. This prevents attackers from confirming record existence.
    """
    scope = _get_scope(current_user)
    record = record_repository.get_record_by_id(db, record_id, user_id=scope)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Record not found", "code": "RECORD_NOT_FOUND"},
        )
    return record


def update_record(db: Session, record_id: str, current_user: User, **kwargs):
    """Full or partial update with ownership check and Cache Invalidation."""
    scope = _get_scope(current_user)
    record = record_repository.get_record_by_id(db, record_id, user_id=scope)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Record not found", "code": "RECORD_NOT_FOUND"},
        )

    updated = record_repository.update_record(db, record, actor_id=current_user.id, **kwargs)
    cache_service.invalidate_prefix("dashboard_")
    return updated


def delete_record(db: Session, record_id: str, current_user: User):
    """Soft-delete with ownership check and Cache Invalidation."""
    scope = _get_scope(current_user)
    record = record_repository.get_record_by_id(db, record_id, user_id=scope)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Record not found", "code": "RECORD_NOT_FOUND"},
        )

    record_repository.soft_delete_record(db, record, actor_id=current_user.id)
    cache_service.invalidate_prefix("dashboard_")
    return {"detail": "Record deleted successfully"}
