"""Audit-log helper. The row is added to the caller's transaction."""

import json
import logging

from fastapi import Request
from sqlalchemy.orm import Session

from backend.models import AuditLog, User

logger = logging.getLogger("portal.audit")


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    # Behind a cloud load balancer the real client IP is in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def record_audit(
    db: Session,
    action: str,
    *,
    user: User | None = None,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
    request: Request | None = None,
) -> None:
    uid = user.user_id if user else user_id
    db.add(
        AuditLog(
            user_id=uid,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=json.dumps(details, default=str) if details else None,
            ip_address=client_ip(request),
        )
    )
    logger.info("AUDIT action=%s user=%s entity=%s:%s", action, uid, entity_type, entity_id)
