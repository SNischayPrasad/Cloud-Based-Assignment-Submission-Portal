"""
Assignment submission workflow:

    submitAssignment() / resubmitAssignment()
        1. check the student is enrolled and the assignment exists
        2. check the deadline with the SERVER clock (SUBMITTED / LATE / rejected)
        3. apply the resubmission policy and idempotency key
        4. validate the file (extension, size, magic bytes)
        5. upload the bytes to OBJECT STORAGE (with retries)
        6. save the METADATA row in the DATABASE
           - if the DB write fails, delete the uploaded object (compensation)
        7. after commit, delete the previous file of a resubmission

    getMySubmissions(), downloadSubmission(), list submissions for a teacher.
"""

import logging
import uuid

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import Enrollment, Role, Submission, SubmissionStatus, User
from backend.schemas.submission import AssignmentSubmissionsOut, DownloadOut, RosterEntry, SubmissionOut
from backend.services import assignment_service, course_service
from backend.services.deadline_policy import can_resubmit, evaluate_submission_time
from backend.utils import time_utils
from backend.utils.audit import record_audit
from backend.utils.errors import ConflictError, ForbiddenError, NotFoundError, ServiceUnavailableError, UnsupportedFileError
from backend.utils.retry import retry_call
from backend.utils.validators import sanitize_filename, scan_for_malware, validate_upload
from cloud.storage_service import StorageError, StorageNotFoundError, get_storage_service

logger = logging.getLogger("portal.submissions")


# --------------------------------------------------------------- helpers
def build_storage_path(assignment_id: int, student_id: int, extension: str, now) -> str:
    """assignments/assignment_001/student_003/20260925T101500Z_3f9a1c2e.pdf

    Generated names (timestamp + random id) mean two uploads never
    overwrite each other and user-controlled text never reaches the key."""
    return (
        f"assignments/assignment_{assignment_id:03d}/student_{student_id:03d}/"
        f"{time_utils.storage_timestamp(now)}_{uuid.uuid4().hex[:8]}.{extension}"
    )


def serialize_submission(submission: Submission) -> SubmissionOut:
    assignment = submission.assignment
    return SubmissionOut(
        submission_id=submission.submission_id,
        assignment_id=submission.assignment_id,
        assignment_title=assignment.title,
        course_code=assignment.course.course_code,
        deadline=assignment.deadline,
        max_marks=assignment.max_marks,
        student_id=submission.student_id,
        student_name=submission.student.name,
        student_email=submission.student.email,
        file_name=submission.file_name,
        file_size=submission.file_size,
        content_type=submission.content_type,
        file_url=submission.file_url,
        storage_path=submission.storage_path,
        checksum_sha256=submission.checksum_sha256,
        submitted_at=submission.submitted_at,
        submission_status=submission.submission_status,
        is_late=submission.is_late,
        attempt_number=submission.attempt_number,
        marks=submission.marks,
        feedback=submission.feedback,
        graded_at=submission.graded_at,
        can_resubmit=can_resubmit(submission, assignment, time_utils.utcnow()),
    )


def get_submission_or_404(db: Session, submission_id: int) -> Submission:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise NotFoundError("Submission not found.")
    return submission


def ensure_can_view_submission(user: User, submission: Submission) -> None:
    """Students: only their own. Teachers: only their courses. Admin: all."""
    if user.role == Role.ADMIN.value:
        return
    if user.role == Role.STUDENT.value:
        if submission.student_id != user.user_id:
            raise ForbiddenError("You can only access your own submissions.", code="SUBMISSION_FORBIDDEN")
        return
    if submission.assignment.course.teacher_id != user.user_id:
        raise ForbiddenError("This submission belongs to a course you do not teach.", code="COURSE_FORBIDDEN")


def _upload_with_retry(path: str, data: bytes, content_type: str):
    storage = get_storage_service()
    return retry_call(
        lambda: storage.upload(path, data, content_type),
        retry_on=(StorageError,),
        attempts=3,
        operation=f"upload {path}",
    )


def _safe_delete(path: str) -> None:
    try:
        get_storage_service().delete(path)
    except StorageError:
        logger.warning("Cleanup of object %s failed - will be caught by storage lifecycle cleanup", path)


# --------------------------------------------------------------- submit
def submit_assignment(
    db: Session,
    student: User,
    assignment_id: int,
    original_filename: str,
    data: bytes,
    idempotency_key: str | None = None,
    request: Request | None = None,
) -> tuple[Submission, bool, bool]:
    """submitAssignment() + resubmitAssignment().

    Returns (submission, replayed, is_resubmission)."""
    assignment = assignment_service.get_assignment_or_404(db, assignment_id)
    if not course_service.is_enrolled(db, student.user_id, assignment.course_id):
        raise ForbiddenError("You are not enrolled in this course.", code="NOT_ENROLLED")

    existing = db.scalar(
        select(Submission).where(Submission.assignment_id == assignment_id, Submission.student_id == student.user_id)
    )

    # Idempotency: the client retried a request that already succeeded
    # (e.g. the connection dropped before the response arrived).
    if existing and idempotency_key and existing.idempotency_key == idempotency_key:
        return existing, True, False

    now = time_utils.utcnow()  # server-side timestamp - the only one we trust
    status, is_late = evaluate_submission_time(assignment, now)

    if existing:
        if existing.submission_status == SubmissionStatus.GRADED.value:
            raise ConflictError("This submission has already been graded and can no longer be replaced.", code="ALREADY_GRADED")
        if not assignment.allow_resubmission:
            raise ConflictError("You have already submitted this assignment and resubmission is disabled.", code="DUPLICATE_SUBMISSION")

    extension, content_type = validate_upload(original_filename, data, assignment.file_types, assignment.max_file_size_mb)
    if not scan_for_malware(data):
        raise UnsupportedFileError("The file was rejected by the malware scanner.", code="MALWARE_DETECTED")
    display_name = sanitize_filename(original_filename)
    storage_path = build_storage_path(assignment_id, student.user_id, extension, now)

    # ---- 1) object storage ----
    try:
        stored = _upload_with_retry(storage_path, data, content_type)
    except StorageError as exc:
        logger.error("Upload failed for assignment=%s student=%s: %s", assignment_id, student.user_id, exc)
        raise ServiceUnavailableError(
            "File storage is temporarily unavailable. Your submission was NOT saved - please try again in a minute.",
            code="STORAGE_UNAVAILABLE",
        ) from exc

    # ---- 2) database metadata ----
    old_path = existing.storage_path if existing else None
    try:
        if existing:
            submission = existing
            submission.attempt_number += 1
        else:
            submission = Submission(assignment_id=assignment_id, student_id=student.user_id, attempt_number=1)
            db.add(submission)
        submission.file_name = display_name
        submission.file_url = stored.uri
        submission.storage_path = stored.path
        submission.file_size = stored.size
        submission.content_type = stored.content_type
        submission.checksum_sha256 = stored.checksum_sha256
        submission.submitted_at = now
        submission.submission_status = status
        submission.is_late = is_late
        submission.idempotency_key = idempotency_key
        db.flush()
        record_audit(
            db,
            "SUBMISSION_REPLACED" if existing else "SUBMISSION_CREATED",
            user=student,
            entity_type="submission",
            entity_id=submission.submission_id,
            details={"assignment_id": assignment_id, "status": status, "attempt": submission.attempt_number,
                     "size": stored.size, "path": stored.path},
            request=request,
        )
        db.commit()
    except IntegrityError as exc:
        # Two first-time submissions raced; the unique constraint kept exactly one.
        db.rollback()
        _safe_delete(storage_path)
        raise ConflictError("A submission for this assignment was just saved. Refresh to see it.", code="DUPLICATE_SUBMISSION") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        _safe_delete(storage_path)  # compensation: don't leave an orphan file
        logger.error("DB write failed after upload; object %s removed: %s", storage_path, exc)
        raise ServiceUnavailableError(
            "The database is temporarily unavailable. Your submission was NOT saved - please try again.",
            code="DATABASE_UNAVAILABLE",
        ) from exc

    if old_path and old_path != storage_path:
        _safe_delete(old_path)

    db.refresh(submission)
    return submission, False, existing is not None


# --------------------------------------------------------------- queries
def get_my_submissions(db: Session, student: User) -> list[SubmissionOut]:
    """getMySubmissions()"""
    rows = db.scalars(
        select(Submission).where(Submission.student_id == student.user_id).order_by(Submission.submitted_at.desc())
    ).unique()
    return [serialize_submission(s) for s in rows]


def get_submission(db: Session, user: User, submission_id: int) -> SubmissionOut:
    submission = get_submission_or_404(db, submission_id)
    ensure_can_view_submission(user, submission)
    return serialize_submission(submission)


def list_assignment_submissions(db: Session, user: User, assignment_id: int) -> AssignmentSubmissionsOut:
    """Teacher view: every enrolled student with their status (incl. NOT_SUBMITTED)."""
    assignment = assignment_service.get_assignment_or_404(db, assignment_id)
    assignment_service.ensure_can_manage(user, assignment)

    enrollments = db.scalars(select(Enrollment).where(Enrollment.course_id == assignment.course_id)).unique()
    submissions = {
        s.student_id: s
        for s in db.scalars(select(Submission).where(Submission.assignment_id == assignment_id)).unique()
    }

    entries: list[RosterEntry] = []
    summary = {"enrolled": 0, "submitted": 0, "not_submitted": 0, "on_time": 0, "late": 0, "graded": 0, "pending_review": 0}
    for enrollment in enrollments:
        summary["enrolled"] += 1
        sub = submissions.pop(enrollment.student_id, None)
        entries.append(_roster_entry(enrollment.student, sub, summary))
    # Submissions from students who later left the course are still shown.
    for sub in submissions.values():
        entries.append(_roster_entry(sub.student, sub, summary))

    order = {"SUBMITTED": 0, "LATE": 1, "GRADED": 2, "NOT_SUBMITTED": 3}
    entries.sort(key=lambda e: (order.get(e.status, 9), e.student_name.lower()))
    return AssignmentSubmissionsOut(
        assignment_id=assignment.assignment_id,
        assignment_title=assignment.title,
        max_marks=assignment.max_marks,
        deadline=assignment.deadline,
        summary=summary,
        entries=entries,
    )


def _roster_entry(student: User, sub: Submission | None, summary: dict[str, int]) -> RosterEntry:
    if sub is None:
        summary["not_submitted"] += 1
        return RosterEntry(student_id=student.user_id, student_name=student.name, student_email=student.email,
                           status=SubmissionStatus.NOT_SUBMITTED.value, submission=None)
    summary["submitted"] += 1
    summary["late" if sub.is_late else "on_time"] += 1
    if sub.submission_status == SubmissionStatus.GRADED.value:
        summary["graded"] += 1
    else:
        summary["pending_review"] += 1
    return RosterEntry(student_id=student.user_id, student_name=student.name, student_email=student.email,
                       status=sub.submission_status, submission=serialize_submission(sub))


# --------------------------------------------------------------- download
def get_download(db: Session, user: User, submission_id: int, disposition: str = "attachment",
                 request: Request | None = None) -> DownloadOut:
    """downloadSubmission() - authorize, then hand out a SHORT-LIVED signed URL.

    The bucket stays private; the URL expires after SIGNED_URL_EXPIRE_SECONDS,
    so a leaked link stops working quickly."""
    submission = get_submission_or_404(db, submission_id)
    ensure_can_view_submission(user, submission)
    settings = get_settings()
    storage = get_storage_service()
    if not storage.exists(submission.storage_path):
        raise NotFoundError("The stored file could not be found. Ask the student to resubmit.", code="FILE_MISSING")
    try:
        url = storage.generate_signed_url(
            submission.storage_path, submission.file_name, disposition, settings.signed_url_expire_seconds
        )
    except StorageNotFoundError as exc:
        raise NotFoundError("The stored file could not be found.", code="FILE_MISSING") from exc
    except StorageError as exc:
        raise ServiceUnavailableError("File storage is temporarily unavailable.", code="STORAGE_UNAVAILABLE") from exc

    record_audit(db, "FILE_ACCESS_GRANTED", user=user, entity_type="submission", entity_id=submission_id,
                 details={"disposition": disposition}, request=request)
    db.commit()
    return DownloadOut(url=url, expires_in=settings.signed_url_expire_seconds,
                       file_name=submission.file_name, disposition=disposition)
