"""
Financial Record routes.

SECURITY: All endpoints pass current_user to the service layer.
The service layer determines data scope based on permissions:
  - Admin users see all records
  - Other users see only their own records
This prevents IDOR attacks at the API boundary.
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, status, Query, Path, Header
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, require_permissions
from app.core.idempotency import idempotency_cache
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
    cursor: Optional[str] = Query(None, description="ISO timestamp cursor for massive datasets"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List financial records with optional filters (ownership-scoped)."""
    return record_service.list_records(
        db=db,
        current_user=current_user,
        record_type=record_type,
        category=category,
        date_from=date_from,
        date_to=date_to,
        search=search,
        cursor=cursor,
        page=page,
        limit=limit
    )

@router.get("/{record_id}", response_model=RecordResponse)
def get_record(
    record_id: str = Path(..., description="The ID of the record"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch a single financial record by ID (ownership-scoped)."""
    return record_service.get_record(db, record_id, current_user)

@router.post("/", response_model=RecordResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions("records:write"))])
def create_record(
    request: RecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key", description="Unique UUID to prevent duplicate transaction entries.")
):
    """Create a new financial record (Admin only)."""
    if idempotency_key:
        cached_response = idempotency_cache.get_response(idempotency_key)
        if cached_response:
            return cached_response

    record = record_service.create_record(
        db=db,
        amount=request.amount,
        record_type=request.type,
        category=request.category,
        record_date=request.date,
        created_by=current_user.id,
        notes=request.notes
    )

    if idempotency_key:
        idempotency_cache.save_response(idempotency_key, record)

    return record

@router.put("/{record_id}", response_model=RecordResponse, dependencies=[Depends(require_permissions("records:write"))])
def update_record(
    request: RecordUpdate,
    record_id: str = Path(..., description="The ID of the record"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full update of an existing record (Admin only, ownership-scoped)."""
    return record_service.update_record(
        db=db,
        record_id=record_id,
        current_user=current_user,
        **request.model_dump()
    )

@router.patch("/{record_id}", response_model=RecordResponse, dependencies=[Depends(require_permissions("records:write"))])
def patch_record(
    request: RecordPartialUpdate,
    record_id: str = Path(..., description="The ID of the record"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Partial update of an existing record (Admin only, ownership-scoped)."""
    return record_service.update_record(
        db=db,
        record_id=record_id,
        current_user=current_user,
        **request.model_dump(exclude_unset=True)
    )

@router.delete("/{record_id}", dependencies=[Depends(require_permissions("records:write"))])
def delete_record(
    record_id: str = Path(..., description="The ID of the record"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a financial record (Admin only, ownership-scoped)."""
    return record_service.delete_record(db, record_id, current_user)
