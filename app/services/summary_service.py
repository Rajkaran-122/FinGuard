"""
Summary Service
================
Dashboard aggregation logic with ownership-scoped data access.

CACHE STRATEGY: Cache-Aside Pattern
  1. Check cache for pre-computed result
  2. On miss: compute from DB, store in cache with TTL
  3. On write (create/update/delete): record_service invalidates dashboard_ keys

WHY SYNC INVALIDATION (not async queue):
  - Assignment scope: Redis/RabbitMQ would add infrastructure complexity
    without demonstrating additional backend thinking
  - The dict-based cache has O(n) key scanning on invalidation, but n is
    bounded by the number of distinct query parameter combinations (typically <100)
  - Production upgrade path: swap cache_service internals to Redis pub/sub
    with zero changes to this service layer (same .get/.set/.invalidate_prefix API)
"""

from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from app.repositories import record_repository
from app.core.cache import cache_service
from app.core.scope import get_data_scope
from app.models.user import User


def get_summary(
    db: Session, current_user: User,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
):
    """
    Get total income, expenses, and net balance via Cache-Aside strategy.

    BUSINESS INSIGHT: When time bounds are provided, calculates
    Month-over-Month (MoM) growth percentages by comparing the
    requested period against the immediately preceding period of
    equal length. This tells stakeholders not just "how much" but
    "how fast" — the metric that drives financial decisions.
    """
    scope = get_data_scope(current_user)
    cache_key = f"dashboard_summary_{scope}_{date_from}_{date_to}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    current = record_repository.get_summary_totals(db, date_from, date_to, user_id=scope)

    # Calculate MoM (Month-over-Month) or Period-over-Period if bounds provided
    mom_income_pct = None
    mom_expense_pct = None

    if date_from and date_to:
        delta = date_to - date_from
        prev_date_to = date_from - timedelta(days=1)
        prev_date_from = prev_date_to - delta

        prev = record_repository.get_summary_totals(db, prev_date_from, prev_date_to, user_id=scope)

        if prev["total_income"] > 0:
            mom_income_pct = round(((current["total_income"] - prev["total_income"]) / prev["total_income"]) * 100, 2)
        elif current["total_income"] > 0:
            mom_income_pct = 100.0

        if prev["total_expenses"] > 0:
            mom_expense_pct = round(((current["total_expenses"] - prev["total_expenses"]) / prev["total_expenses"]) * 100, 2)
        elif current["total_expenses"] > 0:
            mom_expense_pct = 100.0

    current["mom_income_percent"] = mom_income_pct
    current["mom_expense_percent"] = mom_expense_pct

    cache_service.set(cache_key, current, ttl=3600)
    return current


def get_categories(
    db: Session, current_user: User,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
):
    """Get category-wise breakdown scoped by ownership."""
    scope = get_data_scope(current_user)
    cache_key = f"dashboard_categories_{scope}_{date_from}_{date_to}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    breakdowns = record_repository.get_category_breakdown(db, date_from, date_to, user_id=scope)
    income_cats = [b for b in breakdowns if b["type"] == "income"]
    expense_cats = [b for b in breakdowns if b["type"] == "expense"]

    result = {"income_categories": income_cats, "expense_categories": expense_cats}
    cache_service.set(cache_key, result, ttl=3600)
    return result


def get_trends(
    db: Session, current_user: User,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
):
    """Get monthly aggregated trend data scoped by ownership."""
    scope = get_data_scope(current_user)
    cache_key = f"dashboard_trends_{scope}_{date_from}_{date_to}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    trends = record_repository.get_monthly_trends(db, date_from, date_to, user_id=scope)
    result = {"trends": trends, "period_type": "monthly"}
    cache_service.set(cache_key, result, ttl=3600)
    return result


def get_recent(db: Session, current_user: User, limit: int = 10):
    """Get recent financial activity scoped by ownership."""
    scope = get_data_scope(current_user)
    records, total = record_repository.get_recent_records(db, limit, user_id=scope)
    return {
        "records": [
            {
                "id": r.id,
                "amount": float(r.amount),
                "type": r.type.value if hasattr(r.type, 'value') else r.type,
                "category": r.category,
                "date": str(r.date),
                "notes": r.notes,
                "created_at": str(r.created_at),
            }
            for r in records
        ],
        "total": total,
    }
