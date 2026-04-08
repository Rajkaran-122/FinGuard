"""
Authentication Routes (v1)
==========================
Endpoints for user registration, multi-token login, and session refreshing.
"""

from fastapi import APIRouter, Depends, Body, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import auth_service
from app.services.user_service import user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Enroll a new user into the system."""
    return await user_service.create_user(db, user_in.model_dump())


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate via email/password and receive token pair."""
    return await auth_service.login(db, form_data.username, form_data.password)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """Rotate access token using a valid refresh token."""
    return await auth_service.refresh_tokens(db, refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a refresh token and end session."""
    await auth_service.logout(db, refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
