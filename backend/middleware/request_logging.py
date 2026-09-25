"""
Request logging, request IDs, security headers and basic metrics.

Every request gets an X-Request-ID (reused from the load balancer if
present), is timed, and is logged as one structured line. The counters
in METRICS are exposed by /api/health - a tiny version of what
CloudWatch / Azure Monitor / Cloud Monitoring dashboards show.
"""

import logging
import threading
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("portal.request")

_metrics_lock = threading.Lock()
METRICS = {
    "started_at": time.time(),
    "requests_total": 0,
    "responses_4xx": 0,
    "responses_5xx": 0,
    "total_duration_ms": 0.0,
}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def metrics_snapshot() -> dict:
    with _metrics_lock:
        total = METRICS["requests_total"]
        return {
            "uptime_seconds": int(time.time() - METRICS["started_at"]),
            "requests_total": total,
            "responses_4xx": METRICS["responses_4xx"],
            "responses_5xx": METRICS["responses_5xx"],
            "avg_latency_ms": round(METRICS["total_duration_ms"] / total, 2) if total else 0.0,
        }


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            with _metrics_lock:
                METRICS["requests_total"] += 1
                METRICS["total_duration_ms"] += duration_ms
                if 400 <= status_code < 500:
                    METRICS["responses_4xx"] += 1
                elif status_code >= 500:
                    METRICS["responses_5xx"] += 1
            logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%.1f user=%s",
                request_id,
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                getattr(request.state, "user_id", "-"),
            )

        response.headers["X-Request-ID"] = request_id
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response
