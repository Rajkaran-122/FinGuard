"""
Dashboard Pydantic Schemas
==========================
Complex models for aggregated financial analytics and trends.
"""

from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.record import Category
from app.schemas.record import FinancialRecordResponse


class DashboardSummary(BaseModel):
    """Aggregate totals and comparisons."""
    total_income: float
    total_expenses: float
    net_balance: float
    income_growth: float
    expense_growth: float
    current_month_income: float
    current_month_expenses: float
    previous_month_income: float
    previous_month_expenses: float
    record_count: int


class CategoryBreakdown(BaseModel):
    """Spend/Income breakdown by category."""
    category: Category
    total_amount: float
    percentage: float
    transaction_count: int


class TrendData(BaseModel):
    """Time-series data point."""
    period: str  # e.g., "2024-01"
    income: float
    expenses: float
    net: float


class DashboardInsights(BaseModel):
    """High-level analytical insights."""
    top_spending_categories: List[CategoryBreakdown]
    savings_rate: float
    average_daily_spending: float
    largest_expense: Optional[FinancialRecordResponse]
