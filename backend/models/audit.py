"""AUDIT_LOGS and REVOKED_TOKENS tables (security bookkeeping)."""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.types import UTCDateTime
from backend.utils import time_utils
from cloud.database_service import Base


class AuditLog(Base):
    """Who did what, when - e.g. LOGIN, SUBMISSION_CREATED, SUBMISSION_GRADED."""

    __tablename__ = "audit_logs"

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=time_utils.utcnow, index=True, nullable=False)


class RevokedToken(Base):
    """JWT IDs revoked by logout. Checked on every authenticated request."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(UTCDateTime, default=time_utils.utcnow, nullable=False)
