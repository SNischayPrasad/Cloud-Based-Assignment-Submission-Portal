"""
Health / monitoring endpoint.

Load balancers and uptime monitors (Render health checks, AWS ALB target
groups, UptimeRobot) call GET /api/health. It returns 503 when a
dependency is down so the platform can alert or route traffic away.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.middleware.request_logging import metrics_snapshot
from cloud.database_service import check_database_health, get_engine
from cloud.storage_service import get_storage_service

router = APIRouter(tags=["Health"])


@router.get("/api/health", summary="Liveness + dependency health + basic metrics")
def health():
    settings = get_settings()
    database_ok = check_database_health()
    try:
        storage = get_storage_service()
        storage_ok = storage.health_check()
        provider = storage.provider_name
    except Exception:  # noqa: BLE001
        storage_ok, provider = False, settings.storage_provider

    healthy = database_ok and storage_ok
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "environment": settings.environment,
            "checks": {
                "database": {"ok": database_ok, "dialect": get_engine().dialect.name},
                "object_storage": {"ok": storage_ok, "provider": provider},
            },
            "metrics": metrics_snapshot(),
        },
    )


@router.get("/", include_in_schema=False)
def root():
    return {"service": get_settings().app_name, "docs": "/docs", "health": "/api/health"}
