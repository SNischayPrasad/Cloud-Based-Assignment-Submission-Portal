"""COURSES and ENROLLMENTS tables."""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.types import UTCDateTime
from backend.utils import time_utils
from cloud.database_service import Base


class Course(Base):
    __tablename__ = "courses"

    course_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # e.g. CC401
    course_name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # FK -> the teacher who owns the course. Indexed: "my courses" query.
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True, nullable=False)
    # Students join a course with this code (shared by the teacher in class).
    join_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=time_utils.utcnow, nullable=False)

    teacher = relationship("User", lazy="joined")


class Enrollment(Base):
    """Many-to-many link between students and courses."""

    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id", name="uq_enrollment_course_student"),)

    enrollment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"), index=True, nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True, nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(UTCDateTime, default=time_utils.utcnow, nullable=False)

    course = relationship("Course", lazy="joined")
    student = relationship("User", lazy="joined")
