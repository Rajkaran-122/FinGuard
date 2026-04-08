"""
Financial Record Pydantic Schemas
=================================
Validation and response models for financial transactions.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_serializer

from app.models.record import TransactionType, Category


class FinancialRecordBase(BaseModel):
    """Common record attributes."""
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    type: TransactionType
    category: Category
    date: date
    description: Optional[str] = Field(None, max_length=1000)


class FinancialRecordCreate(FinancialRecordBase):
    """Schema for creating a new record."""
    pass


class FinancialRecordUpdate(BaseModel):
    """Schema for updating an existing record."""
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    type: Optional[TransactionType] = None
    category: Optional[Category] = None
    date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=1000)


class FinancialRecordResponse(FinancialRecordBase):
    """Schema for returning record data."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> float:
        """Serialize Decimal amount as float for JSON responses."""
        return float(value)
