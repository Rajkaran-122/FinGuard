"""
Authentication routes.
"""
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.schemas.auth import RegisterRequest, TokenResponse
from app.services import auth_service
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    return auth_service.register_user(
        db=db,
        name=request.name,
        email=request.email,
        password=request.password,
        role=request.role
    )

@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user and return JWT."""
    return auth_service.login_user(db=db, email=form_data.username, password=form_data.password)

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Invalidate session. (Client deletes the token)"""
    return {"detail": "Successfully logged out"}
