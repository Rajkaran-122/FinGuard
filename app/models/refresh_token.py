from __future__ import annotations
"""
Refresh Token ORM Model
=======================
Stores persistent session tokens for JWT rotation.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    @property
    def is_expired(self) -> bool:
        """Check if token is past its expiration date."""
        return datetime.now(timezone.utc) > self.expires_at

    def __repr__(self):
        return f"<RefreshToken user_id={self.user_id} active={not self.is_revoked}>"
