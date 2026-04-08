"""
FastAPI Dependencies
====================
Async dependency injection for database sessions, authentication, and RBAC.
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import security_manager
from app.repositories.user_repository import user_repository
from app.models.user import User, UserRole, UserStatus
from app.core.logging import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decodes JWT token and fetches user from database.
    Ensures user exists and is active.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = security_manager.verify_token(token, "access")
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (ValueError, AttributeError):
        raise credentials_exception

    user = await user_repository.get_by_id(db, user_id)
    if user is None:
        logger.warning(f"auth: user_not_found_in_db user_id={user_id}")
        raise credentials_exception

    if user.status != UserStatus.ACTIVE:
        logger.warning(f"auth: inactive_user_access_attempt user_id={user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    return user


class RoleChecker:
    """
    Dependency for enforcing role-based access control.
    """

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """
        Check if current user has one of the allowed roles.
        """
        if current_user.role not in self.allowed_roles:
            logger.warning(
                f"auth: role_access_denied user_id={current_user.id} role={current_user.role} required={self.allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role: {current_user.role.value}",
            )
        return current_user


# Predefined permission sets
require_admin = RoleChecker([UserRole.ADMIN])
require_analyst_plus = RoleChecker([UserRole.ADMIN, UserRole.ANALYST])
require_any_role = RoleChecker([UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER])
