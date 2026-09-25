"""ASSIGNMENTS table."""

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.types import UTCDateTime
from backend.utils import time_utils
from cloud.database_service import Base


class Assignment(Base):
    __tablename__ = "assignments"
    # Composite index: dashboards ask "assignments of these courses ordered by deadline".
    __table_args__ = (Index("ix_assignments_course_deadline", "course_id", "deadline"),)

    assignment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    deadline: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    # Comma separated list of extensions, e.g. "pdf,docx"
    allowed_file_types: Mapped[str] = mapped_column(String(200), nullable=False)
    max_file_size_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    allow_late_submission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_resubmission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=time_utils.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=time_utils.utcnow, onupdate=time_utils.utcnow, nullable=False
    )

    course = relationship("Course", lazy="joined")

    @property
    def file_types(self) -> list[str]:
        return [t for t in self.allowed_file_types.split(",") if t]
