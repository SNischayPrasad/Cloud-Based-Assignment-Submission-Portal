"""
FastAPI application entry point.

Run locally (from the project root):
    uvicorn backend.app:app --reload --port 8000

Interactive API docs: http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.config import get_settings
from backend.middleware.request_logging import RequestContextMiddleware
from backend.routes import admin, assignments, auth, courses, dashboard, files, health, submissions
from backend.utils.errors import AppError
from backend.utils.logging_config import configure_logging
from cloud.database_service import init_db
from cloud.storage_service import get_storage_service

logger = logging.getLogger("portal.app")

API_DESCRIPTION = """
Cloud-based assignment submission & feedback portal.

* **Authentication** - JWT bearer tokens (`POST /api/login`, then click *Authorize*).
* **Authorization** - role-based (student / teacher / admin) + ownership checks.
* **Cloud database** - SQLAlchemy (SQLite locally, managed PostgreSQL in the cloud).
* **Object storage** - private bucket (local folder or any S3-compatible service) with signed URLs.
"""


def _validation_message(exc: RequestValidationError) -> str:
    parts = []
    for error in exc.errors():
        location = ".".join(str(p) for p in error.get("loc", []) if p not in ("body", "query", "path"))
        message = error.get("msg", "Invalid value").removeprefix("Value error, ")
        parts.append(f"{location}: {message}" if location else message)
    return "; ".join(parts) or "Invalid request."


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_db()  # create tables if missing (use migrations for large production systems)
        get_storage_service()  # fail fast if storage is misconfigured
        logger.info("Started %s (env=%s, storage=%s)", settings.app_name, settings.environment, settings.storage_provider)
        yield
        logger.info("Shutting down")

    app = FastAPI(
        title="Cloud Assignment Submission & Feedback Portal API",
        version="1.0.0",
        description=API_DESCRIPTION,
        lifespan=lifespan,
    )

    # Middleware added last runs first, so CORS wraps everything.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # explicit list - never "*" with auth headers
        allow_credentials=False,  # tokens travel in the Authorization header, not cookies
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    # ---------------- consistent error responses ----------------
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": _validation_message(exc), "code": "VALIDATION_ERROR",
                     "errors": [{k: v for k, v in e.items() if k in ("loc", "msg", "type")} for e in exc.errors()]},
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "The database is temporarily unavailable. Please try again shortly.",
                     "code": "DATABASE_UNAVAILABLE"},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        # Never leak stack traces to clients; the request ID links to the log line.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on the server.", "code": "INTERNAL_ERROR",
                     "request_id": getattr(request.state, "request_id", None)},
        )

    for router in (health.router, auth.router, courses.router, assignments.router,
                   submissions.router, dashboard.router, admin.router, files.router):
        app.include_router(router)

    return app


app = create_app()
