"""
Authentication Service
======================
Handles business logic for user identity, session management, and JWT rotation.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserStatus
from app.core.security import security_manager
from app.repositories.user_repository import user_repository
from app.repositories.token_repository import token_repository
from app.services.audit_service import audit_service
from app.core.logging import logger


class AuthService:
    """
    Orchestrates authentication flows using repositories and security managers.
    """

    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Verify email and password against DB."""
        user = await user_repository.get_by_email(db, email)
        if not user or not security_manager.verify_password(password, user.hashed_password):
            await audit_service.log_event(db, "LOGIN_FAILURE", "AUTH", new_state={"email": email})
            return None
        if user.status != UserStatus.ACTIVE:
            logger.warning(f"auth: login_attempt_inactive_account email={email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active"
            )
        return user

    async def login(self, db: AsyncSession, email: str, password: str) -> Dict[str, Any]:
        """Perform login and generate Access/Refresh token pair."""
        user = await self.authenticate_user(db, email, password)
        if not user:
            logger.info(f"auth: login_failed_invalid_credentials email={email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Generate tokens
        token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
        access_token = security_manager.create_access_token(data=token_data)
        refresh_token = security_manager.create_refresh_token(data={"sub": str(user.id)})

        # Persist refresh token for rotation/revocation
        # Spec says 7 days expiry
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        await token_repository.create(db, {
            "user_id": user.id,
            "token": refresh_token,
            "expires_at": expires_at
        })

        await audit_service.log_event(db, "LOGIN_SUCCESS", "AUTH", user_id=user.id)

        logger.info(f"auth: login_success user_id={user.id}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    async def refresh_tokens(self, db: AsyncSession, refresh_token: str) -> Dict[str, Any]:
        """Rotate access token if refresh token is valid and not revoked."""
        payload = security_manager.verify_token(refresh_token, token_type="refresh")
        user_id = int(payload.get("sub"))

        # Verify against DB (check revocation)
        stored_token = await token_repository.get_by_token(db, refresh_token)
        if not stored_token or stored_token.is_revoked or stored_token.is_expired:
            logger.warning(f"auth: invalid_refresh_token_attempt user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        # Fetch user to get current role/status
        user = await user_repository.get_by_id(db, user_id)
        if not user or user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User unavailable")

        # Generate new access token
        new_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
        new_access_token = security_manager.create_access_token(data=new_data)

        await audit_service.log_event(db, "TOKEN_REFRESH", "AUTH", user_id=user_id)

        logger.info(f"auth: refresh_token_success user_id={user_id}")
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }

    async def logout(self, db: AsyncSession, refresh_token: str):
        """Revoke a refresh token."""
        await token_repository.revoke_token(db, refresh_token)
        logger.info("auth: logout_success")


auth_service = AuthService()
