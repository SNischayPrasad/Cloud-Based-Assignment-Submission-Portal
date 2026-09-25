"""
Central application configuration.

Every setting is read from ENVIRONMENT VARIABLES (optionally loaded from a
`.env` file in the project root). Nothing secret is ever hardcoded here:
the same code runs locally (SQLite + local folder) and in the cloud
(PostgreSQL + S3-compatible object storage) just by changing env vars.
This is the "12-factor app" config principle used by cloud platforms.
"""

import logging
import os
import secrets
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load `.env` if present. Real environment variables always win
# (override=False), which is how cloud hosts inject secrets.
load_dotenv(PROJECT_ROOT / ".env", override=False)

logger = logging.getLogger("portal.config")


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _get_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _normalize_database_url(url: str) -> str:
    # Some hosts (Render, Heroku) hand out "postgres://" URLs, but
    # SQLAlchemy 2.x only accepts the "postgresql://" scheme.
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    # Resolve relative SQLite paths against the project root, so the same
    # database file is used no matter which folder the server is started from.
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        path = Path(url[len("sqlite:///"):])
        if not path.is_absolute() and str(path) != ":memory:":
            return f"sqlite:///{(PROJECT_ROOT / path).resolve().as_posix()}"
    return url


@dataclass(frozen=True)
class Settings:
    # --- General -----------------------------------------------------
    app_name: str
    environment: str  # development | test | production
    log_level: str
    public_api_url: str  # public base URL of this API (used for local signed URLs)

    # --- Security ----------------------------------------------------
    secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    bcrypt_rounds: int
    cors_origins: list[str]
    rate_limit_per_minute: int  # for login/register endpoints

    # --- Database ----------------------------------------------------
    database_url: str

    # --- Object storage ----------------------------------------------
    storage_provider: str  # local | s3
    local_storage_dir: Path
    s3_bucket: str
    s3_region: str
    s3_endpoint_url: str | None
    s3_access_key_id: str | None
    s3_secret_access_key: str | None
    s3_server_side_encryption: str | None
    s3_public_endpoint_url: str | None  # endpoint used in pre-signed URLs, if different
    signed_url_expire_seconds: int

    # --- Upload / submission policy ----------------------------------
    max_upload_mb: int
    allowed_file_types: list[str]
    allow_late_submissions_default: bool
    allow_resubmission_default: bool

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def _resolve_secret_key(environment: str) -> str:
    key = os.getenv("SECRET_KEY", "").strip()
    if key:
        if len(key) < 32:
            logger.warning("SECRET_KEY is shorter than 32 characters - use a longer random value.")
        return key
    if environment == "production":
        raise RuntimeError(
            "SECRET_KEY environment variable is required in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    # Development convenience: an ephemeral random key. Tokens become
    # invalid on every restart, which nudges you to set a real key.
    logger.warning("SECRET_KEY not set - using a random development key (tokens reset on restart).")
    return secrets.token_urlsafe(48)


@lru_cache
def get_settings() -> Settings:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    local_dir = Path(os.getenv("LOCAL_STORAGE_DIR", "storage_data"))
    if not local_dir.is_absolute():
        local_dir = PROJECT_ROOT / local_dir

    return Settings(
        app_name=os.getenv("APP_NAME", "Cloud Assignment Submission Portal"),
        environment=environment,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        public_api_url=os.getenv("PUBLIC_API_URL", "http://localhost:8000").rstrip("/"),
        secret_key=_resolve_secret_key(environment),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=_get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60),
        bcrypt_rounds=max(4, min(15, _get_int("BCRYPT_ROUNDS", 12))),
        cors_origins=_get_list("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"),
        rate_limit_per_minute=_get_int("RATE_LIMIT_PER_MINUTE", 20),
        database_url=_normalize_database_url(
            os.getenv("DATABASE_URL", f"sqlite:///{(PROJECT_ROOT / 'portal.db').as_posix()}")
        ),
        storage_provider=os.getenv("STORAGE_PROVIDER", "local").strip().lower(),
        local_storage_dir=local_dir,
        s3_bucket=os.getenv("S3_BUCKET", ""),
        s3_region=os.getenv("S3_REGION", "us-east-1"),
        s3_endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
        s3_access_key_id=os.getenv("S3_ACCESS_KEY_ID") or None,
        s3_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY") or None,
        s3_server_side_encryption=os.getenv("S3_SERVER_SIDE_ENCRYPTION") or None,
        s3_public_endpoint_url=os.getenv("S3_PUBLIC_ENDPOINT_URL") or None,
        signed_url_expire_seconds=_get_int("SIGNED_URL_EXPIRE_SECONDS", 300),
        max_upload_mb=_get_int("MAX_UPLOAD_MB", 10),
        allowed_file_types=[t.lower().lstrip(".") for t in _get_list("ALLOWED_FILE_TYPES", "pdf,docx,pptx,zip,png,jpg,jpeg,txt,py,ipynb")],
        allow_late_submissions_default=_get_bool("ALLOW_LATE_SUBMISSIONS", True),
        allow_resubmission_default=_get_bool("ALLOW_RESUBMISSION", True),
    )
