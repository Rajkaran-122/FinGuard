"""
Summary Service
================
Dashboard aggregation logic — calls repository, returns dicts.
"""

from datetime import date, timedelta
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

    current = record_repository.get_summary_totals(db, date_from, date_to)
    
    # Calculate Mom (Month-over-Month) or Period-over-Period if bounds provided
    mom_income_pct = None
    mom_expense_pct = None
    
    if date_from and date_to:
        delta = date_to - date_from
        prev_date_to = date_from - timedelta(days=1)
        prev_date_from = prev_date_to - delta
        
        prev = record_repository.get_summary_totals(db, prev_date_from, prev_date_to)
        
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

    cache_service.set(cache_key, current, ttl=3600)  # Cache 1 hour
    return current


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
