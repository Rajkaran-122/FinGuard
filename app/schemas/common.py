"""
Common Pydantic Schemas
=======================
Standardized response wrappers and pagination models.
"""

from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ResponseWrapper(BaseModel, Generic[T]):
    """Standard API response structure."""
    success: bool = True
    message: Optional[str] = "Operation successful"
    data: Optional[T] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated output."""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)
