"""
Financial Record ORM Model
===========================
Represents income/expense transactions with soft-delete support using SQLAlchemy 2.0 style.
"""

import enum
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, DateTime, Enum, ForeignKey, Index, DECIMAL, Boolean, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class TransactionType(str, enum.Enum):
    """Financial record type."""
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class Category(str, enum.Enum):
    """Common financial categories."""
    SALARY = "SALARY"
    BUSINESS = "BUSINESS"
    INVESTMENT = "INVESTMENT"
    FOOD = "FOOD"
    TRANSPORT = "TRANSPORT"
    UTILITIES = "UTILITIES"
    ENTERTAINMENT = "ENTERTAINMENT"
    HEALTHCARE = "HEALTHCARE"
    EDUCATION = "EDUCATION"
    SHOPPING = "SHOPPING"
    OTHER = "OTHER"


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False, index=True)
    category: Mapped[Category] = mapped_column(Enum(Category), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
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
    user: Mapped["User"] = relationship(back_populates="financial_records")

    # Composite indexes for high-performance aggregations
    __table_args__ = (
        Index("idx_records_user_date", "user_id", "date"),
        Index("idx_records_user_type_category", "user_id", "type", "category"),
    )

    def __repr__(self):
        return f"<FinancialRecord {self.type} {self.amount} {self.category}>"
