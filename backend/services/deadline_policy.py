"""
Deadline logic.

    submitted_at <= deadline  ->  SUBMITTED
    submitted_at >  deadline  ->  LATE      (if the assignment allows late work)
                              ->  rejected  (if it does not)

`now` always comes from the server clock (time_utils.utcnow). Both values
are timezone-aware UTC, so a student in IST and a teacher in PST compare
against the same instant.
"""

from datetime import datetime

from backend.models import Assignment, Submission, SubmissionStatus
from backend.utils.errors import ForbiddenError
from backend.utils.time_utils import ensure_utc


def evaluate_submission_time(assignment: Assignment, now: datetime) -> tuple[str, bool]:
    """Return (status, is_late) or raise if the submission window is closed."""
    if ensure_utc(now) <= ensure_utc(assignment.deadline):
        return SubmissionStatus.SUBMITTED.value, False
    if not assignment.allow_late_submission:
        raise ForbiddenError(
            "The deadline for this assignment has passed and late submissions are not accepted.",
            code="DEADLINE_PASSED",
        )
    return SubmissionStatus.LATE.value, True


def is_window_open(assignment: Assignment, now: datetime) -> bool:
    return ensure_utc(now) <= ensure_utc(assignment.deadline) or assignment.allow_late_submission


def can_resubmit(submission: Submission, assignment: Assignment, now: datetime) -> bool:
    return (
        assignment.allow_resubmission
        and submission.submission_status != SubmissionStatus.GRADED.value
        and is_window_open(assignment, now)
    )
