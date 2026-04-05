"""
FastAPI Dependencies
====================
Dependency injection for database sessions, authentication, and RBAC.

Dependency chain for protected requests:
    oauth2_scheme (extract Bearer token)
        -> get_current_user (decode JWT -> fetch user from DB -> check is_active)
            -> require_role("admin") (check role -> raise 403 or pass)
                -> route handler (receives current_user as verified object)
"""

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.core.logging import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db():
    """Yield a database session, ensuring cleanup on completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Decode JWT token, re-fetch user from DB, and validate status.
    Re-fetching ensures deactivated users are blocked immediately.
    """
    from app.models.user import User  # Deferred import to avoid circular deps

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"message": "Could not validate credentials", "code": "AUTH_REQUIRED"},
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        logger.warning("auth_failed: invalid_or_expired_token")
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        logger.warning("auth_failed: missing_subject_claim")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.warning("auth_failed: user_not_found")
        raise credentials_exception

    if not user.is_active:
        logger.warning(f"auth_denied: inactive_user user_id={user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "User account is deactivated", "code": "PERMISSION_DENIED"},
        )

    return user


def require_permissions(*required_permissions: str) -> Callable:
    """
    Returns a dependency that checks the current user's permissions.
    Usage: Depends(require_permissions("records:write", "dashboard:view"))
    """
    def permission_checker(current_user=Depends(get_current_user)):
        user_perms = current_user.permissions or []
        # Check if user has ALL the required permissions
        missing = [p for p in required_permissions if p not in user_perms]
        if missing:
            logger.warning(
                f"auth_denied: missing_permissions user_id={current_user.id} missing={','.join(missing)}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": f"Access denied. Missing permissions: {', '.join(missing)}",
                    "code": "PERMISSION_DENIED",
                    "details": {"missing_permissions": missing},
                },
            )
        return current_user
    return permission_checker
