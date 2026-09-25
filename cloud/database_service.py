"""
Cloud database service.

Creates the SQLAlchemy engine from DATABASE_URL:

* Local development : sqlite:///./portal.db
* Cloud (free tier) : postgresql://user:pass@host:5432/db  (Supabase, Neon, Render, AWS RDS ...)

Only metadata lives in the database (users, courses, assignments,
submission records, marks, feedback). Files live in object storage.
"""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import get_settings

logger = logging.getLogger("portal.database")


class Base(DeclarativeBase):
    """Base class for all ORM models."""


_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    # SQLite ignores FOREIGN KEY constraints unless this pragma is set.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine() -> Engine:
    """Return a process-wide engine (connection pool), creating it lazily."""
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.database_url
        if settings.is_sqlite:
            _engine = create_engine(url, connect_args={"check_same_thread": False})
            event.listen(_engine, "connect", _enable_sqlite_foreign_keys)
        else:
            # Managed PostgreSQL: a small pool with health checks, because
            # cloud databases close idle connections.
            _engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_recycle=1800,
            )
        logger.info("Database engine created (dialect=%s)", _engine.dialect.name)
    return _engine


def get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one database session per HTTP request."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create all tables if they do not exist (idempotent)."""
    import backend.models  # noqa: F401  (registers every model on Base.metadata)

    Base.metadata.create_all(bind=get_engine())
    logger.info("Database tables verified/created")


def drop_all() -> None:
    import backend.models  # noqa: F401

    Base.metadata.drop_all(bind=get_engine())


def check_database_health() -> bool:
    """Used by /api/health - a cheap round trip to the database."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - health checks must never raise
        logger.exception("Database health check failed")
        return False


def reset_engine() -> None:
    """Dispose the engine (used by tests and scripts that change DATABASE_URL)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
