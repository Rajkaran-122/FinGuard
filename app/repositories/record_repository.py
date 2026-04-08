"""
Financial Record Repository
===========================
Data access logic for FinancialRecord model with advanced filtering.
"""

from typing import List, Optional, Tuple
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from app.models.record import FinancialRecord, TransactionType, Category
from app.repositories.base import BaseRepository


class FinancialRecordRepository(BaseRepository[FinancialRecord]):
    """
    Handles persistence logic for financial records with complex filtering.
    """

    def __init__(self):
        super().__init__(FinancialRecord)

    async def get_by_user_with_filters(
        self,
        db: AsyncSession,
        user_id: int,
        type: Optional[TransactionType] = None,
        category: Optional[Category] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[FinancialRecord], int]:
        """
        Retrieves a filtered and paginated list of records for a specific user.
        Also returns the total count for pagination.
        """
        filters = [
            FinancialRecord.user_id == user_id,
            FinancialRecord.is_deleted == False
        ]

        if type:
            filters.append(FinancialRecord.type == type)
        if category:
            filters.append(FinancialRecord.category == category)
        if start_date:
            filters.append(FinancialRecord.date >= start_date)
        if end_date:
            filters.append(FinancialRecord.date <= end_date)
        if min_amount:
            filters.append(FinancialRecord.amount >= min_amount)
        if max_amount:
            filters.append(FinancialRecord.amount <= max_amount)
        if search:
            filters.append(FinancialRecord.description.ilike(f"%{search}%"))

        # Build query
        query = select(FinancialRecord).where(and_(*filters))
        
        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_stmt) or 0
        
        # Get paginated results
        query = query.order_by(FinancialRecord.date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        records = list(result.scalars().all())
        
        return records, total

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        """Marks a record as deleted without removing from DB."""
        result = await db.execute(
            update(FinancialRecord)
            .where(FinancialRecord.id == id)
            .values(is_deleted=True)
        )
        await db.commit()
        return result.rowcount > 0

    async def get_total_by_type(
        self, 
        db: AsyncSession, 
        user_id: int, 
        type: TransactionType,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Decimal:
        """Aggregates total amount for a specific type and time range."""
        filters = [
            FinancialRecord.user_id == user_id,
            FinancialRecord.type == type,
            FinancialRecord.is_deleted == False
        ]
        if start_date:
            filters.append(FinancialRecord.date >= start_date)
        if end_date:
            filters.append(FinancialRecord.date <= end_date)
            
        stmt = select(func.sum(FinancialRecord.amount)).where(and_(*filters))
        result = await db.execute(stmt)
        return result.scalar() or Decimal("0.00")

    async def get_category_breakdown(
        self, db: AsyncSession, user_id: int, type: Optional[TransactionType] = None
    ) -> List[dict]:
        """Returns spend/income breakdown grouped by category."""
        filters = [FinancialRecord.user_id == user_id, FinancialRecord.is_deleted == False]
        if type:
            filters.append(FinancialRecord.type == type)
            
        stmt = (
            select(
                FinancialRecord.category,
                func.sum(FinancialRecord.amount).label("total"),
                func.count(FinancialRecord.id).label("count")
            )
            .where(and_(*filters))
            .group_by(FinancialRecord.category)
        )
        result = await db.execute(stmt)
        return [{"category": r.category, "total": r.total, "count": r.count} for r in result.all()]


record_repository = FinancialRecordRepository()
