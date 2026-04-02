"""
User ORM Model
===============
Represents system users with role-based access control.
"""

import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime, Enum, Index, JSON
from app.core.database import Base


class UserRole(str, enum.Enum):
    """User roles for RBAC enforcement."""
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.VIEWER)
    permissions = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("idx_users_email", "email"),
    )

    def __repr__(self):
        return f"<User {self.email} role={self.role.value}>"
