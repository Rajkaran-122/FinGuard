from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

DataT = TypeVar('DataT')

class ResponseWrapper(BaseModel, Generic[DataT]):
    """Standardized API response wrapper ensuring uniform payload structure."""
    status: str = "success"
    message: Optional[str] = None
    data: DataT
