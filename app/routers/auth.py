"""
Authentication routes.
"""
from fastapi import APIRouter, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.core.rate_limit import limiter
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.common import ResponseWrapper
from app.services import auth_service
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=ResponseWrapper[TokenResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, user_request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    data = auth_service.register_user(
        db=db,
        name=user_request.name,
        email=user_request.email,
        password=user_request.password,
        role=user_request.role
    )
    return {"status": "success", "message": "User registered successfully", "data": data}

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user and return JWT. (Maintains standard OAuth2 format for Swagger UI compatibility)"""
    return auth_service.login_user(db=db, email=form_data.username, password=form_data.password)

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Invalidate session. (Client deletes the token)"""
    return {"status": "success", "message": "Successfully logged out", "data": None}
