"""
Financial Record routes.
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, status, Query, Path
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, require_role
from app.schemas.record import RecordCreate, RecordUpdate, RecordPartialUpdate, RecordResponse, RecordListResponse
from app.services import record_service
from app.models.user import User

router = APIRouter(prefix="/api/records", tags=["Financial Records"])

@router.get("/", response_model=RecordListResponse)
def list_records(
    record_type: Optional[str] = Query(None, description="Filter by type (income/expense)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search term for notes or category"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List financial records with optional filters (All roles)."""
    return record_service.list_records(
        db=db,
        record_type=record_type,
        category=category,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        limit=limit
    )

@router.get("/{record_id}", response_model=RecordResponse)
def get_record(
    record_id: str = Path(..., description="The ID of the record"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch a single financial record by ID (All roles)."""
    return record_service.get_record(db, record_id)

@router.post("/", response_model=RecordResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("admin"))])
def create_record(
    request: RecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new financial record (Admin only)."""
    return record_service.create_record(
        db=db,
        amount=request.amount,
        record_type=request.type,
        category=request.category,
        record_date=request.date,
        created_by=current_user.id,
        notes=request.notes
    )

@router.put("/{record_id}", response_model=RecordResponse, dependencies=[Depends(require_role("admin"))])
def update_record(
    request: RecordUpdate,
    record_id: str = Path(..., description="The ID of the record"),
    db: Session = Depends(get_db)
):
    """Full update of an existing record (Admin only)."""
    return record_service.update_record(
        db=db,
        record_id=record_id,
        **request.model_dump()
    )

@router.patch("/{record_id}", response_model=RecordResponse, dependencies=[Depends(require_role("admin"))])
def patch_record(
    request: RecordPartialUpdate,
    record_id: str = Path(..., description="The ID of the record"),
    db: Session = Depends(get_db)
):
    """Partial update of an existing record (Admin only)."""
    return record_service.update_record(
        db=db,
        record_id=record_id,
        **request.model_dump(exclude_unset=True)
    )

@router.delete("/{record_id}", dependencies=[Depends(require_role("admin"))])
def delete_record(
    record_id: str = Path(..., description="The ID of the record"),
    db: Session = Depends(get_db)
):
    """Soft-delete a financial record (Admin only)."""
    return record_service.delete_record(db, record_id)
