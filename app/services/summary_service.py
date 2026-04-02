"""
Summary Service
================
Dashboard aggregation logic — calls repository, returns dicts.
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from app.repositories import record_repository
from app.core.cache import cache_service


def get_summary(db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None):
    """Get total income, expenses, and net balance via Cache-Aside strategy."""
    cache_key = f"dashboard_summary_{date_from}_{date_to}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    result = record_repository.get_summary_totals(db, date_from, date_to)
    cache_service.set(cache_key, result, ttl=3600)  # Cache 1 hour
    return result


def get_categories(db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None):
    """Get category-wise breakdown heavily optimized by caching bounds."""
    cache_key = f"dashboard_categories_{date_from}_{date_to}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    breakdowns = record_repository.get_category_breakdown(db, date_from, date_to)
    income_cats = [b for b in breakdowns if b["type"] == "income"]
    expense_cats = [b for b in breakdowns if b["type"] == "expense"]
    
    result = {"income_categories": income_cats, "expense_categories": expense_cats}
    cache_service.set(cache_key, result, ttl=3600)
    return result


def get_trends(db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None):
    """Get monthly aggregated trend data offloaded from DB CPU utilizing cache blocks."""
    cache_key = f"dashboard_trends_{date_from}_{date_to}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    trends = record_repository.get_monthly_trends(db, date_from, date_to)
    result = {"trends": trends, "period_type": "monthly"}
    cache_service.set(cache_key, result, ttl=3600)
    return result


def get_recent(db: Session, limit: int = 10):
    """Get recent financial activity."""
    records, total = record_repository.get_recent_records(db, limit)
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
