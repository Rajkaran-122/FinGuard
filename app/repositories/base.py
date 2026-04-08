"""
Generic Base Repository
=======================
Handles standard CRUD operations using Async SQLAlchemy 2.0.
Provides a foundation for domain-specific repositories.
"""

from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Abstract base class for all repositories.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_by_id(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """Fetch a single record by its primary key."""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Fetch multiple records with optional filtering and pagination."""
        query = select(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new database record."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, id: Any, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """Update an existing record."""
        await db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**obj_in)
        )
        await db.commit()
        return await self.get_by_id(db, id)

    async def delete(self, db: AsyncSession, id: Any) -> bool:
        """Permanently delete a record."""
        result = await db.execute(delete(self.model).where(self.model.id == id))
        await db.commit()
        return result.rowcount > 0

    async def count(self, db: AsyncSession, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get the total count of records matching filters."""
        query = select(func.count()).select_from(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        result = await db.execute(query)
        return result.scalar() or 0
