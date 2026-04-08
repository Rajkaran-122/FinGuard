"""
Dashboard Service
=================
Aggregates financial data into actionable insights and summary metrics.
Implements high-performance caching for heavy aggregations.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.record import TransactionType
from app.repositories.record_repository import record_repository
from app.services.cache_service import cache_service
from app.core.logging import logger


class DashboardService:
    """
    Handles complex aggregations and cross-domain insights.
    """

    async def get_summary(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """
        Calculates total income, expenses, and growth metrics.
        Cached for 5 minutes.
        """
        cache_key = f"dashboard:summary:{user_id}"
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return cached_data

        now = datetime.now()
        current_month_start = date(now.year, now.month, 1)
        prev_month_end = current_month_start - timedelta(days=1)
        prev_month_start = date(prev_month_end.year, prev_month_end.month, 1)

        # Totals
        total_income = await record_repository.get_total_by_type(db, user_id, TransactionType.INCOME)
        total_expenses = await record_repository.get_total_by_type(db, user_id, TransactionType.EXPENSE)

        # Current Month
        curr_income = await record_repository.get_total_by_type(db, user_id, TransactionType.INCOME, current_month_start)
        curr_expenses = await record_repository.get_total_by_type(db, user_id, TransactionType.EXPENSE, current_month_start)

        # Previous Month
        prev_income = await record_repository.get_total_by_type(db, user_id, TransactionType.INCOME, prev_month_start, prev_month_end)
        prev_expenses = await record_repository.get_total_by_type(db, user_id, TransactionType.EXPENSE, prev_month_start, prev_month_end)

        # Growth Calculations
        income_growth = self._calculate_growth(curr_income, prev_income)
        expense_growth = self._calculate_growth(curr_expenses, prev_expenses)

        summary = {
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_balance": float(total_income - total_expenses),
            "current_month_income": float(curr_income),
            "current_month_expenses": float(curr_expenses),
            "previous_month_income": float(prev_income),
            "previous_month_expenses": float(prev_expenses),
            "income_growth": income_growth,
            "expense_growth": expense_growth
        }

        await cache_service.set(cache_key, summary, ttl=300)
        return summary

    async def get_category_breakdown(
        self, db: AsyncSession, user_id: int, type: Optional[TransactionType] = None
    ) -> List[Dict[str, Any]]:
        """Calculates spend/income percentages by category."""
        breakdown = await record_repository.get_category_breakdown(db, user_id, type)
        total_sum = sum(Decimal(str(item["total"])) for item in breakdown)
        
        results = []
        for item in breakdown:
            amount = Decimal(str(item["total"]))
            results.append({
                "category": item["category"],
                "total_amount": float(amount),
                "transaction_count": item["count"],
                "percentage": round(float((amount / total_sum) * 100), 2) if total_sum > 0 else 0.0
            })
        
        return sorted(results, key=lambda x: x["total_amount"], reverse=True)

    async def get_trends(self, db: AsyncSession, user_id: int, months: int = 6) -> List[Dict[str, Any]]:
        """
        Retrieves monthly income vs expense trends.
        Currently simulated via monthly aggregations in a loop (optimization target).
        """
        trends = []
        now = datetime.now()
        for i in range(months - 1, -1, -1):
            # Calculate month range
            target_date = now - timedelta(days=i * 30)
            month_start = date(target_date.year, target_date.month, 1)
            if target_date.month == 12:
                month_end = date(target_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)
            
            income = await record_repository.get_total_by_type(db, user_id, TransactionType.INCOME, month_start, month_end)
            expenses = await record_repository.get_total_by_type(db, user_id, TransactionType.EXPENSE, month_start, month_end)
            
            trends.append({
                "period": month_start.strftime("%Y-%m"),
                "income": float(income),
                "expenses": float(expenses),
                "net": float(income - expenses)
            })
        return trends

    def _calculate_growth(self, current: Decimal, previous: Decimal) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(float(((current - previous) / previous) * 100), 2)


dashboard_service = DashboardService()
