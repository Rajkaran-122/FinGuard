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
    """
    Register a new user via the public endpoint.

    SECURITY: The client-provided 'role' is IGNORED. All self-registered
    users are assigned 'viewer' with minimal permissions. Elevated roles
    (analyst, admin) must be granted by an existing admin via /api/users.
    This prevents privilege-escalation attacks on the public registration endpoint.
    """
    existing = user_repository.get_user_by_email(db, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "A user with this email already exists", "code": "VALIDATION_FAILED"},
        )

    # SECURITY: Force viewer role on public registration — ignore client input
    safe_role = "viewer"

    user = user_repository.create_user(
        db=db,
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=safe_role,
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
            detail={"message": "Invalid email or password", "code": "AUTH_REQUIRED"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "User account is deactivated", "code": "PERMISSION_DENIED"},
        )

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "name": user.name,
    }
