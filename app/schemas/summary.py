"""Dashboard summary response schemas."""

from typing import List, Optional
from pydantic import BaseModel


class SummaryResponse(BaseModel):
    """Total income, expenses, and net balance."""
    total_income: float
    total_expenses: float
    net_balance: float
    record_count: int
    mom_income_percent: Optional[float] = None
    mom_expense_percent: Optional[float] = None


class CategoryBreakdown(BaseModel):
    """Single category aggregate."""
    category: str
    type: str
    total: float
    count: int


class CategoryResponse(BaseModel):
    """Category-wise breakdown for income and expenses."""
    income_categories: List[CategoryBreakdown]
    expense_categories: List[CategoryBreakdown]


class TrendDataPoint(BaseModel):
    """Single data point in a time-series trend."""
    period: str  # e.g., "2025-01"
    income: float
    expense: float
    net: float


class TrendResponse(BaseModel):
    """Monthly/weekly aggregated trend data."""
    trends: List[TrendDataPoint]
    period_type: str = "monthly"


class RecentRecordItem(BaseModel):
    """Simplified record for recent activity feed."""
    id: str
    amount: float
    type: str
    category: str
    date: str
    notes: Optional[str] = None
    created_at: str


class RecentActivityResponse(BaseModel):
    """Recent financial activity."""
    records: List[RecentRecordItem]
    total: int
