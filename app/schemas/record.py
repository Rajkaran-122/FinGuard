"""Financial record request/response schemas."""

from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    """Schema for creating a financial record."""
    amount: Decimal = Field(..., gt=0, decimal_places=2, examples=[5000.00])
    type: str = Field(..., pattern="^(income|expense)$", examples=["income"])
    category: str = Field(..., min_length=1, max_length=100, examples=["Salary"])
    date: date = Field(..., examples=["2025-01-15"])
    notes: Optional[str] = Field(None, max_length=500, examples=["Monthly salary"])


class RecordUpdate(BaseModel):
    """Schema for full update of a financial record."""
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    type: str = Field(..., pattern="^(income|expense)$")
    category: str = Field(..., min_length=1, max_length=100)
    date: date
    notes: Optional[str] = Field(None, max_length=500)


class RecordPartialUpdate(BaseModel):
    """Schema for partial update — all fields optional."""
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    type: Optional[str] = Field(None, pattern="^(income|expense)$")
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)


class RecordResponse(BaseModel):
    """Schema for financial record response."""
    id: str
    amount: float
    type: str
    category: str
    date: date
    notes: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecordListResponse(BaseModel):
    """Paginated record list response."""
    records: List[RecordResponse]
    total: int
    page: int = 1
    limit: int = 50
    next_cursor: Optional[str] = None
