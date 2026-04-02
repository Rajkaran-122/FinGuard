"""
User Repository
================
All database queries related to users.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.user import User, UserRole


def create_user(db: Session, name: str, email: str, password_hash: str, role: str) -> User:
    """Create a new user record."""
    user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        role=UserRole(role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Fetch a user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Fetch a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_all_users(db: Session) -> List[User]:
    """Fetch all users ordered by creation date."""
    return db.query(User).order_by(User.created_at.desc()).all()


def update_user_role(db: Session, user: User, role: str) -> User:
    """Update a user's role."""
    user.role = UserRole(role)
    db.commit()
    db.refresh(user)
    return user


def update_user_status(db: Session, user: User, is_active: bool) -> User:
    """Toggle a user's active/inactive status."""
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    """Permanently delete a user."""
    db.delete(user)
    db.commit()


def count_admins(db: Session) -> int:
    """Count active admin users — prevents deleting the last admin."""
    return db.query(User).filter(
        User.role == UserRole.ADMIN,
        User.is_active == True
    ).count()
