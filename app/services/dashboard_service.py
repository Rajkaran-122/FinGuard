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

        # Total Record Count
        record_count = await record_repository.count(db, filters={"user_id": user_id, "is_deleted": False})

        summary = {
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_balance": float(total_income - total_expenses),
            "current_month_income": float(curr_income),
            "current_month_expenses": float(curr_expenses),
            "previous_month_income": float(prev_income),
            "previous_month_expenses": float(prev_expenses),
            "income_growth": income_growth,
            "expense_growth": expense_growth,
            "record_count": record_count
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
        Retrieves monthly income vs expense trends using bulk aggregation.
        """
        start_date = (datetime.now() - timedelta(days=months * 30)).date().replace(day=1)
        data = await record_repository.get_monthly_trends_bulk(db, user_id, start_date)
        
        # Format results into expected structure
        trends_map = {}
        for r in data:
            period = f"{r['year']}-{r['month']:02d}"
            if period not in trends_map:
                trends_map[period] = {"period": period, "income": 0.0, "expenses": 0.0}
            
            if r["type"] == TransactionType.INCOME:
                trends_map[period]["income"] = float(r["total"])
            else:
                trends_map[period]["expenses"] = float(r["total"])

        # Calculate net and sort
        results = []
        for period in sorted(trends_map.keys()):
            item = trends_map[period]
            item["net"] = round(item["income"] - item["expenses"], 2)
            results.append(item)
            
        return results

    def _calculate_growth(self, current: Decimal, previous: Decimal) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(float(((current - previous) / previous) * 100), 2)


dashboard_service = DashboardService()
