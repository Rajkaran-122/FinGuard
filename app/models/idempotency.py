"""
Idempotency Key ORM Model
=========================
Persists idempotent write responses so duplicate requests can be short‑circuited.
Compatible with PostgreSQL (JSONB) and SQLite (JSON).
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Column,
    String,
    DateTime,
    JSON,
    Index,
    Text,
)
from app.core.database import Base


class IdempotencyKey(Base):
    """Stored idempotent responses keyed by client-provided header."""

    __tablename__ = "idempotency_keys"

    key = Column(String(100), primary_key=True)
    request_fingerprint = Column(String(128), nullable=False)
    user_id = Column(String(36), nullable=False)
    response_body = Column(JSON().with_variant(Text, "sqlite"), nullable=True)
    status = Column(String(20), nullable=False, default="completed")
    ttl_expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1),
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_idempotency_ttl", "ttl_expires_at"),
        Index("idx_idempotency_user", "user_id"),
    )
