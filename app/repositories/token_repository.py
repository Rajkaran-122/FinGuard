"""
Refresh Token Repository
=========================
Data access logic for the RefreshToken model.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """
    Handles persistence logic for refresh tokens.
    """

    def __init__(self):
        super().__init__(RefreshToken)

    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[RefreshToken]:
        """Find a token entry by its unique string."""
        result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
        return result.scalar_one_or_none()

    async def revoke_token(self, db: AsyncSession, token: str) -> bool:
        """Mark a token as revoked."""
        result = await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token == token)
            .values(is_revoked=True)
        )
        await db.commit()
        return result.rowcount > 0


token_repository = RefreshTokenRepository()
