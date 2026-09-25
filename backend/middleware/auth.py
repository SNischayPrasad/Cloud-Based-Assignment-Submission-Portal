"""
Authentication and role-based authorization dependencies.

AUTHENTICATION ("Who are you?")
    get_current_user validates the Bearer JWT: signature, expiry, issuer,
    not revoked by logout, and the account still exists and is active.

AUTHORIZATION ("What are you allowed to do?")
    require_roles("teacher") rejects users whose role is not allowed.
    Finer, resource-level checks (e.g. "is this YOUR submission?",
    "is this YOUR course?") live in the service layer.

The role is read from the DATABASE, not trusted from the token, so a
role change or account suspension takes effect immediately.
"""

from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.models import RevokedToken, User
from backend.utils.errors import ForbiddenError, UnauthorizedError
from cloud.auth_service import AuthError, decode_access_token
from cloud.database_service import get_db

bearer_scheme = HTTPBearer(auto_error=False, description="Paste the access_token returned by POST /api/login")


@dataclass
class AuthContext:
    user: User
    claims: dict


def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Authentication required. Log in and send the token as 'Authorization: Bearer <token>'.")

    try:
        claims = decode_access_token(credentials.credentials)
    except AuthError as exc:
        raise UnauthorizedError(str(exc), code="TOKEN_INVALID") from exc

    if db.get(RevokedToken, claims["jti"]) is not None:
        raise UnauthorizedError("This session was logged out. Please log in again.", code="TOKEN_REVOKED")

    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("Account not found or disabled.", code="ACCOUNT_DISABLED")

    request.state.user_id = user.user_id  # picked up by the request logger
    return AuthContext(user=user, claims=claims)


def get_current_user(context: AuthContext = Depends(get_auth_context)) -> User:
    return context.user


def require_roles(*roles: str):
    """Dependency factory: `Depends(require_roles("teacher", "admin"))`."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError(
                f"Access denied: this action requires the {' or '.join(roles)} role.", code="ROLE_FORBIDDEN"
            )
        return user

    return dependency


require_student = require_roles("student")
require_teacher = require_roles("teacher", "admin")
require_admin = require_roles("admin")
