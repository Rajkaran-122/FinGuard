"""
Security Utilities
==================
Enterprise-grade security manager handling password hashing and JWT lifecycle.
Supports Access and Refresh token pairs.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    """ Manages authentication and authorization tokens. """

    def __init__(self):
        self.pwd_context = pwd_context
        self.algorithm = settings.JWT_ALGORITHM
        self.access_secret = settings.JWT_SECRET
        self.refresh_secret = settings.JWT_REFRESH_SECRET

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain-text password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Create a bcrypt hash of a password."""
        return self.pwd_context.hash(password)

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Generate a short-lived access JWT."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire, "type": "access", "iat": datetime.now(timezone.utc)})
        return jwt.encode(to_encode, self.access_secret, algorithm=self.algorithm)

    def create_refresh_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Generate a long-lived refresh JWT."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        to_encode.update({"exp": expire, "type": "refresh", "iat": datetime.now(timezone.utc)})
        return jwt.encode(to_encode, self.refresh_secret, algorithm=self.algorithm)

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Validate and decode a JWT.
        Raises 401 if invalid or wrong type.
        """
        try:
            secret = self.access_secret if token_type == "access" else self.refresh_secret
            payload = jwt.decode(token, secret, algorithms=[self.algorithm])
            if payload.get("type") != token_type:
                raise JWTError("Invalid token type claim")
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Singleton instance
security_manager = SecurityManager()

# Functional aliases for backward compatibility and convenience
def get_password_hash(password: str) -> str:
    return security_manager.get_password_hash(password)

def hash_password(password: str) -> str:
    """Alias for get_password_hash to support legacy tests."""
    return get_password_hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return security_manager.verify_password(plain_password, hashed_password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    return security_manager.create_access_token(data, expires_delta)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Helper for decoding access tokens, returns None on failure instead of raising."""
    try:
        return security_manager.verify_token(token, "access")
    except HTTPException:
        return None
