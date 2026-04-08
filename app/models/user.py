from __future__ import annotations
"""
User ORM Model
==============
Represents system users with role-based access control using SQLAlchemy 2.0 style.
"""

import enum
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import String, DateTime, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.record import FinancialRecord
    from app.models.refresh_token import RefreshToken
    from app.models.audit_log import AuditLog


class UserRole(str, enum.Enum):
    """User roles for RBAC enforcement."""
    VIEWER = "VIEWER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    """User operational status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    
    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    financial_records: Mapped[List[FinancialRecord]] = relationship(back_populates="user", cascade="all, delete-orphan")
    refresh_tokens: Mapped[List[RefreshToken]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[List[AuditLog]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email} role={self.role}>"
