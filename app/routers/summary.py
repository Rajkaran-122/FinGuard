"""
Dashboard Summary routes.

SECURITY: All endpoints pass current_user to the service layer for
ownership-scoped data access. Viewers see only their own aggregations.
Admins see organization-wide totals.
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, require_permissions
from app.schemas.summary import SummaryResponse, CategoryResponse, TrendResponse, RecentActivityResponse
from app.services import summary_service
from app.models.user import User

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard Summary"])

@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns total income, expenses, and net balance (ownership-scoped)."""
    return summary_service.get_summary(db, current_user, date_from, date_to)

@router.get("/categories", response_model=CategoryResponse, dependencies=[Depends(require_permissions("dashboard:view"))])
def get_categories(
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Category-wise income and expense breakdown (ownership-scoped)."""
    return summary_service.get_categories(db, current_user, date_from, date_to)

@router.get("/recent", response_model=RecentActivityResponse)
def get_recent(
    limit: int = Query(10, ge=1, le=100, description="Number of recent records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Recent transactions (ownership-scoped)."""
    return summary_service.get_recent(db, current_user, limit)

@router.get("/trends", response_model=TrendResponse, dependencies=[Depends(require_permissions("dashboard:view"))])
def get_trends(
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Monthly/weekly aggregated trend data (ownership-scoped)."""
    return summary_service.get_trends(db, current_user, date_from, date_to)
