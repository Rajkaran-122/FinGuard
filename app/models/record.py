"""
Financial Record ORM Model
===========================
Represents income/expense transactions with soft-delete support.
"""

import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Numeric, Date, Text, DateTime,
    Enum, ForeignKey, Index,
)
from app.core.database import Base


class RecordType(str, enum.Enum):
    """Financial record type."""
    INCOME = "income"
    EXPENSE = "expense"


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(Enum(RecordType), nullable=False)
    category = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
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

    # Indexes for common query patterns
    __table_args__ = (
        Index("idx_records_date", "date"),
        Index("idx_records_type", "type"),
        Index("idx_records_category", "category"),
        Index("idx_records_created_by", "created_by"),
    )

    def __repr__(self):
        return f"<FinancialRecord {self.type.value} {self.amount} {self.category}>"

class FinancialRecordAudit(Base):
    """Immutable audit log capturing exact changes preventing historical data loss."""
    __tablename__ = "financial_record_audits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    record_id = Column(String(36), ForeignKey("financial_records.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(50), nullable=False) 
    old_state = Column(Text, nullable=True)
    new_state = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_audit_record_id", "record_id"),
    )

