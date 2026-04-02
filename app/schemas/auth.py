"""Auth request/response schemas."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Schema for user registration."""
    name: str = Field(..., min_length=1, max_length=255, examples=["Rajkaran Yadav"])
    email: EmailStr = Field(..., examples=["admin@finance.dev"])
    password: str = Field(..., min_length=6, max_length=128, examples=["Admin@123"])
    role: str = Field(default="viewer", pattern="^(viewer|analyst|admin)$", examples=["admin"])


class LoginRequest(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., examples=["admin@finance.dev"])
    password: str = Field(..., examples=["Admin@123"])


class TokenResponse(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    name: str
