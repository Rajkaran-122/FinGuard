"""
User Service
============
Handles business logic for user management, profile updates, and RBAC administration.
"""

from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import user_repository
from app.core.security import security_manager
from app.core.logging import logger


class UserService:
    """
    Manages user lifecycle and administrative actions.
    """

    async def get_users(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None
    ) -> Tuple[List[User], int]:
        """List users with pagination and filters."""
        filters = {}
        if role:
            filters["role"] = role
        if status:
            filters["status"] = status
            
        users = await user_repository.get_multi(db, skip, limit, filters)
        total = await user_repository.count(db, filters)
        return users, total

    async def create_user(self, db: AsyncSession, user_data: dict) -> User:
        """Register a new user with hashed password."""
        existing = await user_repository.get_by_email(db, user_data["email"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password before storage
        password = user_data.pop("password")
        user_data["hashed_password"] = security_manager.get_password_hash(password)
        
        user = await user_repository.create(db, user_data)
        logger.info(f"user: created user_id={user.id} role={user.role}")
        return user

    async def update_user(self, db: AsyncSession, user_id: int, update_data: dict) -> User:
        """Update user details or status (Admin only)."""
        user = await user_repository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        updated_user = await user_repository.update(db, user_id, update_data)
        logger.info(f"user: updated user_id={user_id}")
        return updated_user

    async def get_user(self, db: AsyncSession, user_id: int) -> User:
        """Fetch a specific user profile."""
        user = await user_repository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user


user_service = UserService()
