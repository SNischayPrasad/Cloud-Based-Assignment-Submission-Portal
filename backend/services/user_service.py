"""Registration, login, logout and admin user management."""

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.middleware.auth import AuthContext
from backend.models import AuditLog, RevokedToken, Role, User
from backend.schemas.auth import RegisterRequest
from backend.schemas.user import AdminCreateUser, AdminUpdateUser
from backend.utils import time_utils
from backend.utils.audit import record_audit
from backend.utils.errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from cloud.auth_service import create_access_token, hash_password, verify_password


@lru_cache
def _dummy_hash() -> str:
    # Used to spend the same bcrypt time when an email does not exist,
    # so response timing does not reveal which emails are registered.
    return hash_password("timing-attack-protection-1")


def _email_taken(db: Session, email: str) -> bool:
    return db.scalar(select(User.user_id).where(User.email == email)) is not None


def register_student(db: Session, data: RegisterRequest, request: Request | None = None) -> User:
    email = data.email.lower()
    if _email_taken(db, email):
        raise ConflictError("An account with this email already exists. Log in instead.", code="EMAIL_EXISTS")
    user = User(name=data.name, email=email, password_hash=hash_password(data.password), role=Role.STUDENT.value)
    db.add(user)
    db.flush()
    record_audit(db, "USER_REGISTERED", user=user, entity_type="user", entity_id=user.user_id, request=request)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str, request: Request | None = None) -> tuple[User, str, int]:
    """Return (user, access_token, expires_in_seconds) or raise 401."""
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        verify_password(password, _dummy_hash())
        record_audit(db, "LOGIN_FAILED", details={"email": email.lower()}, request=request)
        db.commit()
        raise UnauthorizedError("Incorrect email or password.", code="INVALID_CREDENTIALS")

    if not verify_password(password, user.password_hash):
        record_audit(db, "LOGIN_FAILED", user=user, request=request)
        db.commit()
        raise UnauthorizedError("Incorrect email or password.", code="INVALID_CREDENTIALS")

    if not user.is_active:
        raise UnauthorizedError("This account has been disabled. Contact the administrator.", code="ACCOUNT_DISABLED")

    token, _jti, _expires_at = create_access_token(user.user_id, user.role)
    record_audit(db, "LOGIN_SUCCESS", user=user, request=request)
    db.commit()
    return user, token, get_settings().access_token_expire_minutes * 60


def logout(db: Session, context: AuthContext, request: Request | None = None) -> None:
    """Revoke the current token's jti so it can never be used again."""
    claims = context.claims
    expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    if db.get(RevokedToken, claims["jti"]) is None:
        db.add(RevokedToken(jti=claims["jti"], user_id=context.user.user_id, expires_at=expires_at))
    # Housekeeping: revoked entries are useless once the token has expired anyway.
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < time_utils.utcnow()))
    record_audit(db, "LOGOUT", user=context.user, request=request)
    db.commit()


# ------------------------------------------------------------------ admin
def list_users(db: Session, role: str | None = None) -> list[User]:
    query = select(User).order_by(User.role, User.name)
    if role:
        query = query.where(User.role == role)
    return list(db.scalars(query))


def create_user(db: Session, admin: User, data: AdminCreateUser, request: Request | None = None) -> User:
    email = data.email.lower()
    if _email_taken(db, email):
        raise ConflictError("An account with this email already exists.", code="EMAIL_EXISTS")
    user = User(name=data.name.strip(), email=email, password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.flush()
    record_audit(db, "USER_CREATED", user=admin, entity_type="user", entity_id=user.user_id,
                 details={"role": data.role}, request=request)
    db.commit()
    return user


def update_user(db: Session, admin: User, user_id: int, data: AdminUpdateUser, request: Request | None = None) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    changes = data.model_dump(exclude_unset=True)
    if user.user_id == admin.user_id and (changes.get("role", "admin") != "admin" or changes.get("is_active") is False):
        raise ForbiddenError("You cannot remove your own admin access or disable your own account.")
    for field, value in changes.items():
        setattr(user, field, value)
    record_audit(db, "USER_UPDATED", user=admin, entity_type="user", entity_id=user.user_id,
                 details=changes, request=request)
    db.commit()
    return user


def list_audit_logs(db: Session, limit: int = 100, action: str | None = None) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.audit_id.desc()).limit(limit)
    if action:
        query = query.where(AuditLog.action == action)
    return list(db.scalars(query))
