"""AUTH endpoints: POST /api/register, POST /api/login, POST /api/logout, GET /api/me"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.middleware.auth import AuthContext, get_auth_context, get_current_user
from backend.middleware.rate_limit import auth_rate_limiter
from backend.models import User
from backend.schemas.auth import LoginRequest, MessageResponse, RegisterRequest, TokenResponse
from backend.schemas.user import UserOut
from backend.services import user_service
from cloud.database_service import get_db

router = APIRouter(prefix="/api", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limiter)],
    summary="Register a new student account",
)
def register(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    return user_service.register_student(db, data, request)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(auth_rate_limiter)],
    summary="Log in and receive a JWT access token",
)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user, token, expires_in = user_service.authenticate(db, data.email, data.password, request)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/logout", response_model=MessageResponse, summary="Revoke the current access token")
def logout(request: Request, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    user_service.logout(db, context, request)
    return MessageResponse(message="Logged out. This token can no longer be used.")


@router.get("/me", response_model=UserOut, summary="Current user profile (token check)")
def me(user: User = Depends(get_current_user)):
    return user
