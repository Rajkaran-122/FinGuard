"""
User routes.
"""
from fastapi import APIRouter, Depends, status, Path
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, require_permissions
from app.schemas.user import UserCreate, UserResponse, UserListResponse, UserRoleUpdate, UserStatusUpdate
from app.schemas.common import ResponseWrapper
from app.services import user_service
from app.models.user import User

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/", response_model=ResponseWrapper[UserListResponse], dependencies=[Depends(require_permissions("users:manage"))])
def list_users(db: Session = Depends(get_db)):
    """List all users (Admin, Analyst)."""
    data = user_service.list_users(db)
    return {"status": "success", "message": "Users retrieved successfully", "data": data}

@router.get("/me", response_model=ResponseWrapper[UserResponse])
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return {"status": "success", "message": "Profile retrieved successfully", "data": current_user}

@router.post("/", response_model=ResponseWrapper[UserResponse], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions("users:manage"))])
def create_user(request: UserCreate, db: Session = Depends(get_db)):
    """Create a new user (Admin only)."""
    data = user_service.create_user(
        db=db,
        name=request.name,
        email=request.email,
        password=request.password,
        role=request.role,
    )
    return {"status": "success", "message": "User created successfully", "data": data}

@router.patch("/{user_id}/role", response_model=ResponseWrapper[UserResponse], dependencies=[Depends(require_permissions("users:manage"))])
def update_user_role(
    request: UserRoleUpdate,
    user_id: str = Path(..., description="The ID of the user to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a user's role (Admin only)."""
    data = user_service.update_role(db, user_id, request.role, current_user)
    return {"status": "success", "message": "User role updated successfully", "data": data}

@router.patch("/{user_id}/status", response_model=ResponseWrapper[UserResponse], dependencies=[Depends(require_permissions("users:manage"))])
def update_user_status(
    request: UserStatusUpdate,
    user_id: str = Path(..., description="The ID of the user to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle a user's active/inactive status (Admin only)."""
    data = user_service.toggle_status(db, user_id, request.is_active, current_user)
    return {"status": "success", "message": "User status updated successfully", "data": data}

@router.delete("/{user_id}", dependencies=[Depends(require_permissions("users:manage"))])
def delete_user(
    user_id: str = Path(..., description="The ID of the user to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a user (Admin only)."""
    data = user_service.delete_user(db, user_id, current_user)
    return {"status": "success", "message": "User deleted successfully", "data": data}
