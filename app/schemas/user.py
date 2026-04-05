"""User request/response schemas."""

from datetime import datetime
from typing import List
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a user (admin action)."""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="viewer", pattern="^(viewer|analyst|admin)$")


class UserRoleUpdate(BaseModel):
    """Schema for updating a user's role."""
    role: str = Field(..., pattern="^(viewer|analyst|admin)$")


class UserStatusUpdate(BaseModel):
    """Schema for toggling user active/inactive status."""
    is_active: bool


class UserResponse(BaseModel):
    """Schema for user response — never exposes password_hash."""
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserResponse]
    total: int
