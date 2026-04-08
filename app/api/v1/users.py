"""
User Management Routes (v1)
===========================
Administrative endpoints for managing system users and RBAC.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin, require_analyst_plus
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserResponse, UserUpdate, UserCreate
from app.schemas.common import PaginatedResponse
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    role: Optional[UserRole] = None,
    user_status: Optional[UserStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_plus)
):
    """Admin/Analyst: List all users with pagination and filters."""
    users, total = await user_service.get_users(db, skip, limit, role, user_status)
    return {
        "items": users,
        "total": total,
        "page": (skip // limit) + 1,
        "size": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_plus)
):
    """Admin/Analyst: Fetch a specific user profile."""
    return await user_service.get_user(db, user_id)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin: Directly create a new user with specific role/status."""
    return await user_service.create_user(db, user_in.model_dump())


@router.patch("/{user_id}", response_model=UserResponse)
async def patch_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin: Update user role, status, or profile info."""
    return await user_service.update_user(db, user_id, user_update.model_dump(exclude_unset=True))
