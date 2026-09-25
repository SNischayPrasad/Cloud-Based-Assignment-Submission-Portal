"""SUBMISSIONS table - metadata only; the file itself lives in object storage."""

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.types import UTCDateTime
from cloud.database_service import Base


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        # One active submission per student per assignment (resubmission updates it).
        UniqueConstraint("assignment_id", "student_id", name="uq_submission_assignment_student"),
        # Teacher views: "submissions of assignment X with status Y".
        Index("ix_submissions_assignment_status", "assignment_id", "submission_status"),
    )

    submission_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.assignment_id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True, nullable=False)

    # ---- file reference (NOT the file bytes) ----
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)      # original name shown to users
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)       # provider URI: local://... or s3://bucket/key
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)   # object key inside the bucket
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)  # integrity check

    # ---- workflow ----
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)  # server time, never client time
    submission_status: Mapped[str] = mapped_column(String(20), nullable=False)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # kept even after grading
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ---- grading ----
    marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    graded_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)

    assignment = relationship("Assignment", lazy="joined")
    student = relationship("User", foreign_keys=[student_id], lazy="joined")
