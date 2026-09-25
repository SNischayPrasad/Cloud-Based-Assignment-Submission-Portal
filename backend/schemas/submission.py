from datetime import datetime

from pydantic import BaseModel, Field


class SubmissionOut(BaseModel):
    submission_id: int
    assignment_id: int
    assignment_title: str
    course_code: str
    deadline: datetime
    max_marks: float
    student_id: int
    student_name: str
    student_email: str
    file_name: str
    file_size: int
    content_type: str
    file_url: str
    storage_path: str
    checksum_sha256: str
    submitted_at: datetime
    submission_status: str
    is_late: bool
    attempt_number: int
    marks: float | None
    feedback: str | None
    graded_at: datetime | None
    can_resubmit: bool = False


class SubmitResult(BaseModel):
    submission: SubmissionOut
    message: str
    replayed: bool = Field(default=False, description="True when an identical Idempotency-Key request was already processed")


class GradeRequest(BaseModel):
    marks: float = Field(ge=0, description="Must not exceed the assignment's max_marks")
    feedback: str = Field(default="", max_length=5000)


class FeedbackOut(BaseModel):
    submission_id: int
    assignment_id: int
    assignment_title: str
    submission_status: str
    is_late: bool
    marks: float | None
    max_marks: float
    feedback: str | None
    graded_at: datetime | None
    graded_by_name: str | None


class DownloadOut(BaseModel):
    url: str
    expires_in: int
    file_name: str
    disposition: str


class RosterEntry(BaseModel):
    student_id: int
    student_name: str
    student_email: str
    status: str  # NOT_SUBMITTED | SUBMITTED | LATE | GRADED
    submission: SubmissionOut | None


class AssignmentSubmissionsOut(BaseModel):
    assignment_id: int
    assignment_title: str
    max_marks: float
    deadline: datetime
    summary: dict[str, int]
    entries: list[RosterEntry]
