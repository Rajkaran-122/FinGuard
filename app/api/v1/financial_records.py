"""
Financial Record Routes (v1)
============================
End-to-end management of financial transactions with advanced filtering.
Ownership is strictly enforced or Admin access is required.
Idempotency-Key header is honoured on POST to prevent duplicate submissions.
"""

from typing import Optional
from decimal import Decimal
from datetime import date
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_analyst_plus, require_any_role
from app.core.idempotency import idempotency_manager, make_fingerprint
from app.models.user import User
from app.models.record import TransactionType, Category
from app.schemas.record import FinancialRecordResponse, FinancialRecordCreate, FinancialRecordUpdate
from app.schemas.common import PaginatedResponse
from app.services.record_service import record_service
from app.repositories.record_repository import record_repository

router = APIRouter(prefix="/records", tags=["Financial Records"])


@router.get("", response_model=PaginatedResponse[FinancialRecordResponse])
async def list_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    type: Optional[TransactionType] = None,
    category: Optional[Category] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role)
):
    """Fetch user's financial records with advanced multi-parameter filtering."""
    records, total = await record_service.get_records(
        db, current_user.id, skip, limit, type=type, category=category,
        start_date=start_date, end_date=end_date, min_amount=min_amount,
        max_amount=max_amount, search=search
    )
    return {
        "items": records,
        "total": total,
        "page": (skip // limit) + 1,
        "size": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/{record_id}", response_model=FinancialRecordResponse)
async def get_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """Fetch a single record by ID. Returns 404 if not owned by the current user (IDOR protection)."""
    from app.models.user import UserRole
    record = await record_repository.get_by_id(db, record_id)
    if not record or record.is_deleted:
        raise HTTPException(status_code=404, detail="Record not found")
    # Non-admin users can only see their own records
    if record.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.post("", response_model=FinancialRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_new_record(
    request: Request,
    record_in: FinancialRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_plus),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Analyst/Admin: Log a new transaction. Supports idempotent submission via Idempotency-Key header."""

    if idempotency_key:
        fingerprint = make_fingerprint(
            method=request.method,
            path=str(request.url.path),
            body=record_in.model_dump(mode="json"),
            user_id=str(current_user.id),
        )

        async def _create():
            record = await record_service.create_record(db, current_user.id, record_in.model_dump())
            # Serialize to dict for storage, using the response schema
            return FinancialRecordResponse.model_validate(record).model_dump(mode="json")

        stored = await idempotency_manager.process(
            db=db,
            key=idempotency_key,
            fingerprint=fingerprint,
            user_id=str(current_user.id),
            compute_response=_create,
        )

        # If idempotency returned a cached dict, re-fetch the live ORM object
        # or reconstruct the response directly from the stored dict.
        if isinstance(stored, dict) and "id" in stored:
            record = await record_repository.get_by_id(db, stored["id"])
            if record:
                return record
            # Fallback: return via schema (handles the cached-dict case)
            return FinancialRecordResponse(**stored)

        return stored

    # No idempotency key — plain creation
    return await record_service.create_record(db, current_user.id, record_in.model_dump())


@router.patch("/{record_id}", response_model=FinancialRecordResponse)
async def update_existing_record(
    record_id: int,
    record_update: FinancialRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_plus)
):
    """Analyst/Admin: Modify a transaction (ownership or Admin role required)."""
    return await record_service.update_record(db, record_id, current_user, record_update.model_dump(exclude_unset=True))


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record_entry(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_plus)
):
    """Analyst/Admin: Remove a transaction (Soft-delete)."""
    await record_service.delete_record(db, record_id, current_user)
    return None
