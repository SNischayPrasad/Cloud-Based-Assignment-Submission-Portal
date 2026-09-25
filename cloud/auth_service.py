"""
Authentication service.

* Passwords are hashed with bcrypt (salted, slow by design) - the plain
  password is never stored or logged.
* Sessions are stateless JWT access tokens signed with SECRET_KEY.
  Each token carries a unique `jti` so it can be revoked on logout.

In a managed-cloud deployment this module is the single place you would
replace with AWS Cognito / Firebase Auth / Supabase Auth token verification.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from backend.config import get_settings

# bcrypt only uses the first 72 bytes of a password; we reject longer ones
# instead of silently truncating them.
BCRYPT_MAX_BYTES = 72


class AuthError(Exception):
    """Raised when a token is missing, malformed, expired or tampered with."""


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        raise ValueError("Password is too long (maximum 72 bytes).")
    # Cost factor 12 = ~0.25 s per hash: slow for attackers, fine for users.
    # (The automated tests lower it via BCRYPT_ROUNDS to stay fast.)
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": "assignment-portal",
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires_at


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer="assignment-portal",
            options={"require": ["sub", "jti", "exp", "role"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Your session has expired. Please log in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid authentication token.") from exc
