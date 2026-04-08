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
    total_income: Decimal
    total_expenses: Decimal
    net_balance: Decimal
    income_growth: float
    expense_growth: float
    current_month_income: Decimal
    current_month_expenses: Decimal
    previous_month_income: Decimal
    previous_month_expenses: Decimal


class CategoryBreakdown(BaseModel):
    """Spend/Income breakdown by category."""
    category: Category
    total_amount: Decimal
    percentage: float
    transaction_count: int


class TrendData(BaseModel):
    """Time-series data point."""
    period: str  # e.g., "2024-01"
    income: Decimal
    expenses: Decimal
    net: Decimal


class DashboardInsights(BaseModel):
    """High-level analytical insights."""
    top_spending_categories: List[CategoryBreakdown]
    savings_rate: float
    average_daily_spending: Decimal
    largest_expense: Optional[FinancialRecordResponse]
