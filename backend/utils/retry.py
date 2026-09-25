"""
Retry with exponential backoff + jitter.

Cloud services occasionally fail for a moment (network blip, throttling).
Retrying a SAFE (idempotent) operation a few times hides these transient
faults. Uploading the same bytes to the same object key is idempotent,
so storage uploads are retried; non-idempotent actions are not.
"""

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")
logger = logging.getLogger("portal.retry")


def retry_call(
    func: Callable[[], T],
    *,
    retry_on: tuple[type[BaseException], ...],
    attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 2.0,
    operation: str = "operation",
) -> T:
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except retry_on as exc:
            last_error = exc
            if attempt == attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1))) + random.uniform(0, base_delay)
            logger.warning("%s failed (attempt %d/%d): %s - retrying in %.2fs", operation, attempt, attempts, exc, delay)
            time.sleep(delay)
    assert last_error is not None
    raise last_error
