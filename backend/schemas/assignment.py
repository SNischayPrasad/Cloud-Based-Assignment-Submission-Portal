from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.schemas.validation import clean_text
from backend.utils.time_utils import ensure_utc


class AssignmentBase(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=10000)
    deadline: datetime = Field(description="ISO-8601. Naive values are treated as UTC.")
    max_marks: float = Field(gt=0, le=1000)
    allowed_file_types: list[str] | str = Field(default="pdf", examples=[["pdf", "docx"]])
    max_file_size_mb: int = Field(default=10, ge=1, le=100)
    allow_late_submission: bool | None = None  # None -> portal default (ALLOW_LATE_SUBMISSIONS)
    allow_resubmission: bool | None = None  # None -> portal default (ALLOW_RESUBMISSION)

    _clean_title = field_validator("title")(clean_text)

    @field_validator("deadline")
    @classmethod
    def deadline_to_utc(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class AssignmentCreate(AssignmentBase):
    course_id: int


class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    deadline: datetime | None = None
    max_marks: float | None = Field(default=None, gt=0, le=1000)
    allowed_file_types: list[str] | str | None = None
    max_file_size_mb: int | None = Field(default=None, ge=1, le=100)
    allow_late_submission: bool | None = None
    allow_resubmission: bool | None = None

    @field_validator("deadline")
    @classmethod
    def deadline_to_utc(cls, value: datetime | None) -> datetime | None:
        return ensure_utc(value) if value else value


class AssignmentOut(BaseModel):
    assignment_id: int
    course_id: int
    course_code: str
    course_name: str
    title: str
    description: str
    deadline: datetime
    max_marks: float
    allowed_file_types: list[str]
    max_file_size_mb: int
    allow_late_submission: bool
    allow_resubmission: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    is_past_deadline: bool
    # Student view: status of MY submission. Teacher view: counts.
    my_status: str | None = None
    my_submission_id: int | None = None
    submission_count: int | None = None
    enrolled_count: int | None = None
