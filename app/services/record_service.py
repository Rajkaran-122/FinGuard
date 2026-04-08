"""
Financial Record Service
========================
Business logic for managing financial transactions.
Handles ownership validation and cache invalidation on mutation.
"""

from typing import List, Optional, Tuple
from decimal import Decimal
from datetime import date
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.record import FinancialRecord, TransactionType, Category
from app.models.user import User, UserRole
from app.repositories.record_repository import record_repository
from app.services.cache_service import cache_service
from app.core.logging import logger


class RecordService:
    """
    Orchestrates financial data operations with security checks.
    """

    async def get_records(
        self,
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        type: Optional[TransactionType] = None,
        category: Optional[Category] = None,
        **filters
    ) -> Tuple[List[FinancialRecord], int]:
        """Fetch filtered records for the current user."""
        return await record_repository.get_by_user_with_filters(
            db, user_id, type, category, skip=skip, limit=limit, **filters
        )

    async def create_record(self, db: AsyncSession, user_id: int, record_data: dict) -> FinancialRecord:
        """Create a new record and invalidate dashboard cache."""
        record_data["user_id"] = user_id
        record = await record_repository.create(db, record_data)
        
        # Invalidate dashboard cache immediately on mutation
        await cache_service.delete(f"dashboard:summary:{user_id}")
        
        logger.info(f"record: created record_id={record.id} user_id={user_id}")
        return record

    async def update_record(self, db: AsyncSession, record_id: int, current_user: User, update_data: dict) -> FinancialRecord:
        """Update a record if existing and owned by user (or Admin)."""
        record = await record_repository.get_by_id(db, record_id)
        if not record or record.is_deleted:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Security/Ownership Check
        if record.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            logger.warning(f"record: unauthorized_update_attempt record_id={record_id} user_id={current_user.id}")
            raise HTTPException(status_code=403, detail="Not authorized to update this record")

        updated = await record_repository.update(db, record_id, update_data)
        await cache_service.delete(f"dashboard:summary:{record.user_id}")
        
        logger.info(f"record: updated record_id={record_id}")
        return updated

    async def delete_record(self, db: AsyncSession, record_id: int, current_user: User) -> bool:
        """Soft delete a record (Admin or Owner)."""
        record = await record_repository.get_by_id(db, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # Security/Ownership Check
        if record.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Not authorized to delete this record")

        success = await record_repository.soft_delete(db, record_id)
        if success:
            await cache_service.delete(f"dashboard:summary:{record.user_id}")
            logger.info(f"record: soft_deleted record_id={record_id}")
        return success


record_service = RecordService()
