"""
Auth Service
=============
Login, registration logic. Pure business rules — no FastAPI imports.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.repositories import user_repository


def register_user(db: Session, name: str, email: str, password: str, role: str) -> dict:
    """Register a new user. Raises 400 if email already exists."""
    existing = user_repository.get_user_by_email(db, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    user = user_repository.create_user(
        db=db,
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "name": user.name,
    }


def login_user(db: Session, email: str, password: str) -> dict:
    """Authenticate user and return JWT. Raises 401 on failure."""
    user = user_repository.get_user_by_email(db, email)

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "name": user.name,
    }
