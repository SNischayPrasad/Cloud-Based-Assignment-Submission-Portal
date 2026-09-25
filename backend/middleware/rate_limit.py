"""
In-memory sliding-window rate limiter.

Protects login/registration from brute-force attempts. Because the
counters live in this process's memory, each server instance counts
separately - in a multi-instance cloud deployment you would move this
to Redis, or enforce it at the edge (API Gateway throttling, Cloudflare,
AWS WAF rate-based rules).
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from backend.config import get_settings
from backend.utils.audit import client_ip
from backend.utils.errors import RateLimitedError


class RateLimiter:
    def __init__(self, scope: str, window_seconds: int = 60):
        self.scope = scope
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def __call__(self, request: Request) -> None:
        limit = get_settings().rate_limit_per_minute
        key = client_ip(request) or "unknown"
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = int(self.window - (now - hits[0])) + 1
                raise RateLimitedError(f"Too many attempts. Try again in {retry_after} seconds.")
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


auth_rate_limiter = RateLimiter(scope="auth")
