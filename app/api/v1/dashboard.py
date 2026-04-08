"""
Dashboard Analytics Routes (v1)
===============================
Consolidated endpoints for financial summaries, trends, and category breakdowns.
Leverages high-performance transit and caching.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_any_role
from app.models.user import User
from app.models.record import TransactionType
from app.schemas.dashboard import DashboardSummary, CategoryBreakdown, TrendData
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role)
):
    """Retrieves high-level summary of income, expenses, and growth."""
    return await dashboard_service.get_summary(db, current_user.id)


@router.get("/categories", response_model=List[CategoryBreakdown])
async def get_category_aggregations(
    type: Optional[TransactionType] = Query(None, description="Filter by Income or Expense"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role)
):
    """Calculates distribution of funds across various categories."""
    return await dashboard_service.get_category_breakdown(db, current_user.id, type)


@router.get("/trends", response_model=List[TrendData])
async def get_monthly_trends(
    months: int = Query(6, ge=1, le=12, description="Number of months to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role)
):
    """Calculates time-series data for income vs expense comparison."""
    return await dashboard_service.get_trends(db, current_user.id, months)
