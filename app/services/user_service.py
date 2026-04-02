"""
User Service
=============
User management business rules.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.repositories import user_repository


def create_user(db: Session, name: str, email: str, password: str, role: str):
    """Create a new user (admin action). Raises 400 if email exists."""
    existing = user_repository.get_user_by_email(db, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    return user_repository.create_user(db, name, email, hash_password(password), role)


def list_users(db: Session):
    """List all users with their roles and statuses."""
    users = user_repository.get_all_users(db)
    return {"users": users, "total": len(users)}


def get_user(db: Session, user_id: str):
    """Get a single user by ID."""
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def update_role(db: Session, user_id: str, role: str, current_user):
    """Update a user's role. Cannot demote self if last admin."""
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent last admin from demoting themselves
    if user.id == current_user.id and role != "admin":
        admin_count = user_repository.count_admins(db)
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last admin user",
            )

    return user_repository.update_user_role(db, user, role)


def toggle_status(db: Session, user_id: str, is_active: bool, current_user):
    """Toggle user active/inactive. Cannot deactivate self."""
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_user.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    return user_repository.update_user_status(db, user, is_active)


def delete_user(db: Session, user_id: str, current_user):
    """Delete a user. Cannot delete self or last admin."""
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    if user.role.value == "admin":
        admin_count = user_repository.count_admins(db)
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin user",
            )

    user_repository.delete_user(db, user)
    return {"detail": "User deleted successfully"}
