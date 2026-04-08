"""
User Repository
===============
Data access logic for the User model.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Handles persistence logic for users.
    """

    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Fetch a user by their unique email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


user_repository = UserRepository()
