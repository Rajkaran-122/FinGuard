"""
Authentication Pydantic Schemas
==============================
Models for tokens and login requests.
"""

from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserResponse


class Token(BaseModel):
    """Access and Refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Payload decoded from access token."""
    sub: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    """Standard email/password login."""
    email: str
    password: str
