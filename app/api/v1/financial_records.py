"""
Financial Record Routes (v1)
============================
End-to-end management of financial transactions with advanced filtering.
Ownership is strictly enforced or Admin access is required.
"""

from typing import Optional
from decimal import Decimal
from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_analyst_plus, require_any_role
from app.models.user import User
from app.models.record import TransactionType, Category
from app.schemas.record import FinancialRecordResponse, FinancialRecordCreate, FinancialRecordUpdate
from app.schemas.common import PaginatedResponse
from app.services.record_service import record_service

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


@router.post("", response_model=FinancialRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_new_record(
    record_in: FinancialRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_plus)
):
    """Analyst/Admin: Log a new transaction."""
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
