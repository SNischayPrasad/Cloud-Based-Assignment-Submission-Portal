"""
Server-side time helpers.

All deadline decisions use `utcnow()` on the SERVER. Client clocks can be
wrong or deliberately changed, so a timestamp sent by the browser is
never trusted for "was this submitted on time?".

Code elsewhere calls `time_utils.utcnow()` (module attribute access) so
tests can monkeypatch the clock to simulate late submissions.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC and convert aware ones to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def storage_timestamp(value: datetime) -> str:
    """Compact, sortable timestamp for object keys, e.g. 20260925T101500Z."""
    return ensure_utc(value).strftime("%Y%m%dT%H%M%SZ")
