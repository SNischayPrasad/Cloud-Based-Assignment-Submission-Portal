"""
Feedback & grading: gradeSubmission(), getSubmissionFeedback().

Rules enforced on the server (the UI hiding a button is not security):
* only the teacher of the course (or an admin) can grade
* 0 <= marks <= assignment.max_marks
* students can read, but never write, marks and feedback
"""

from fastapi import Request
from sqlalchemy.orm import Session

from backend.models import Role, SubmissionStatus, User
from backend.schemas.submission import FeedbackOut, GradeRequest, SubmissionOut
from backend.services import assignment_service
from backend.services.submission_service import (
    ensure_can_view_submission,
    get_submission_or_404,
    serialize_submission,
)
from backend.utils import time_utils
from backend.utils.audit import record_audit
from backend.utils.errors import ForbiddenError, ValidationFailed


def grade_submission(db: Session, user: User, submission_id: int, data: GradeRequest,
                     request: Request | None = None) -> SubmissionOut:
    """gradeSubmission() - also used to update an existing grade."""
    submission = get_submission_or_404(db, submission_id)
    assignment = submission.assignment
    if user.role == Role.STUDENT.value or not assignment_service.can_manage(user, assignment):
        raise ForbiddenError("Only the teacher of this course can grade this submission.", code="GRADE_FORBIDDEN")

    if data.marks > assignment.max_marks:
        raise ValidationFailed(
            f"Marks ({data.marks:g}) cannot exceed the maximum of {assignment.max_marks:g} for this assignment.",
            code="MARKS_EXCEED_MAXIMUM",
        )

    previous = submission.marks
    submission.marks = round(data.marks, 2)
    submission.feedback = data.feedback.strip() or None
    submission.graded_at = time_utils.utcnow()
    submission.graded_by = user.user_id
    submission.submission_status = SubmissionStatus.GRADED.value  # is_late is preserved separately

    record_audit(
        db,
        "SUBMISSION_REGRADED" if previous is not None else "SUBMISSION_GRADED",
        user=user,
        entity_type="submission",
        entity_id=submission_id,
        details={"marks": submission.marks, "previous_marks": previous, "max_marks": assignment.max_marks},
        request=request,
    )
    db.commit()
    db.refresh(submission)
    return serialize_submission(submission)


def get_submission_feedback(db: Session, user: User, submission_id: int) -> FeedbackOut:
    """getSubmissionFeedback()"""
    submission = get_submission_or_404(db, submission_id)
    ensure_can_view_submission(user, submission)
    grader = db.get(User, submission.graded_by) if submission.graded_by else None
    return FeedbackOut(
        submission_id=submission.submission_id,
        assignment_id=submission.assignment_id,
        assignment_title=submission.assignment.title,
        submission_status=submission.submission_status,
        is_late=submission.is_late,
        marks=submission.marks,
        max_marks=submission.assignment.max_marks,
        feedback=submission.feedback,
        graded_at=submission.graded_at,
        graded_by_name=grader.name if grader else None,
    )
