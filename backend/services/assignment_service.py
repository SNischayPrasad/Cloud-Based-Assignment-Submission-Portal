"""
Assignment management: createAssignment, updateAssignment, deleteAssignment,
getAssignments, getAssignmentById.
"""

import logging

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import Assignment, Enrollment, Role, Submission, User
from backend.schemas.assignment import AssignmentCreate, AssignmentOut, AssignmentUpdate
from backend.services import course_service
from backend.utils import time_utils
from backend.utils.audit import record_audit
from backend.utils.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailed
from backend.utils.validators import normalize_file_types
from cloud.storage_service import StorageError, get_storage_service

logger = logging.getLogger("portal.assignments")


# --------------------------------------------------------------- helpers
def get_assignment_or_404(db: Session, assignment_id: int) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise NotFoundError("Assignment not found.")
    return assignment


def can_manage(user: User, assignment: Assignment) -> bool:
    return course_service.can_manage_course(user, assignment.course)


def ensure_can_view(db: Session, user: User, assignment: Assignment) -> None:
    if user.role == Role.ADMIN.value:
        return
    if user.role == Role.TEACHER.value:
        if assignment.course.teacher_id != user.user_id:
            raise ForbiddenError("You can only view assignments of courses you teach.", code="COURSE_FORBIDDEN")
        return
    if not course_service.is_enrolled(db, user.user_id, assignment.course_id):
        raise ForbiddenError("You are not enrolled in this course.", code="NOT_ENROLLED")


def ensure_can_manage(user: User, assignment: Assignment) -> None:
    if not can_manage(user, assignment):
        raise ForbiddenError("Only the teacher of this course can change this assignment.", code="COURSE_FORBIDDEN")


def _validate_limits(file_types, max_file_size_mb: int | None) -> list[str] | None:
    settings = get_settings()
    if max_file_size_mb is not None and max_file_size_mb > settings.max_upload_mb:
        raise ValidationFailed(f"Maximum file size cannot exceed the portal limit of {settings.max_upload_mb} MB.")
    if file_types is None:
        return None
    return normalize_file_types(file_types, settings.allowed_file_types)


def serialize_assignment(
    assignment: Assignment,
    *,
    my_submission: Submission | None = None,
    include_my_status: bool = False,
    submission_count: int | None = None,
    enrolled_count: int | None = None,
) -> AssignmentOut:
    now = time_utils.utcnow()
    my_status = None
    if include_my_status:
        my_status = my_submission.submission_status if my_submission else "NOT_SUBMITTED"
    return AssignmentOut(
        assignment_id=assignment.assignment_id,
        course_id=assignment.course_id,
        course_code=assignment.course.course_code,
        course_name=assignment.course.course_name,
        title=assignment.title,
        description=assignment.description,
        deadline=assignment.deadline,
        max_marks=assignment.max_marks,
        allowed_file_types=assignment.file_types,
        max_file_size_mb=assignment.max_file_size_mb,
        allow_late_submission=assignment.allow_late_submission,
        allow_resubmission=assignment.allow_resubmission,
        created_by=assignment.created_by,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        is_past_deadline=now > assignment.deadline,
        my_status=my_status,
        my_submission_id=my_submission.submission_id if my_submission else None,
        submission_count=submission_count,
        enrolled_count=enrolled_count,
    )


def _submission_counts(db: Session, assignment_ids: list[int]) -> dict[int, int]:
    if not assignment_ids:
        return {}
    return dict(
        db.execute(
            select(Submission.assignment_id, func.count(Submission.submission_id))
            .where(Submission.assignment_id.in_(assignment_ids))
            .group_by(Submission.assignment_id)
        ).all()
    )


def _enrolled_counts(db: Session, course_ids: list[int]) -> dict[int, int]:
    if not course_ids:
        return {}
    return dict(
        db.execute(
            select(Enrollment.course_id, func.count(Enrollment.enrollment_id))
            .where(Enrollment.course_id.in_(course_ids))
            .group_by(Enrollment.course_id)
        ).all()
    )


# --------------------------------------------------------------- actions
def create_assignment(db: Session, user: User, data: AssignmentCreate, request: Request | None = None) -> AssignmentOut:
    """createAssignment()"""
    settings = get_settings()
    course = course_service.get_course_for_manager(db, user, data.course_id)
    if data.deadline <= time_utils.utcnow():
        raise ValidationFailed("The deadline must be in the future.")
    file_types = _validate_limits(data.allowed_file_types, data.max_file_size_mb)

    assignment = Assignment(
        course_id=course.course_id,
        title=data.title,
        description=data.description.strip(),
        deadline=data.deadline,
        max_marks=data.max_marks,
        allowed_file_types=",".join(file_types),
        max_file_size_mb=data.max_file_size_mb,
        allow_late_submission=(
            settings.allow_late_submissions_default if data.allow_late_submission is None else data.allow_late_submission
        ),
        allow_resubmission=(
            settings.allow_resubmission_default if data.allow_resubmission is None else data.allow_resubmission
        ),
        created_by=user.user_id,
    )
    db.add(assignment)
    db.flush()
    record_audit(db, "ASSIGNMENT_CREATED", user=user, entity_type="assignment", entity_id=assignment.assignment_id,
                 details={"title": assignment.title, "course_id": course.course_id}, request=request)
    db.commit()
    db.refresh(assignment)
    return serialize_assignment(assignment, submission_count=0, enrolled_count=_enrolled_counts(db, [course.course_id]).get(course.course_id, 0))


def update_assignment(db: Session, user: User, assignment_id: int, data: AssignmentUpdate, request: Request | None = None) -> AssignmentOut:
    """updateAssignment()"""
    assignment = get_assignment_or_404(db, assignment_id)
    ensure_can_manage(user, assignment)
    changes = data.model_dump(exclude_unset=True)

    if "deadline" in changes and changes["deadline"] is not None and changes["deadline"] <= time_utils.utcnow():
        raise ValidationFailed("The new deadline must be in the future.")
    if "allowed_file_types" in changes or "max_file_size_mb" in changes:
        file_types = _validate_limits(changes.get("allowed_file_types"), changes.get("max_file_size_mb"))
        if file_types is not None:
            changes["allowed_file_types"] = ",".join(file_types)
    if "max_marks" in changes and changes["max_marks"] is not None:
        highest = db.scalar(select(func.max(Submission.marks)).where(Submission.assignment_id == assignment_id))
        if highest is not None and changes["max_marks"] < highest:
            raise ValidationFailed(f"Maximum marks cannot be lower than a mark already awarded ({highest:g}).")
    if "title" in changes and changes["title"] is not None:
        changes["title"] = changes["title"].strip()

    for field, value in changes.items():
        if value is not None:
            setattr(assignment, field, value)
    record_audit(db, "ASSIGNMENT_UPDATED", user=user, entity_type="assignment", entity_id=assignment_id,
                 details={k: v for k, v in changes.items() if k != "description"}, request=request)
    db.commit()
    db.refresh(assignment)
    counts = _submission_counts(db, [assignment_id])
    return serialize_assignment(
        assignment,
        submission_count=counts.get(assignment_id, 0),
        enrolled_count=_enrolled_counts(db, [assignment.course_id]).get(assignment.course_id, 0),
    )


def delete_assignment(db: Session, user: User, assignment_id: int, force: bool = False, request: Request | None = None) -> int:
    """deleteAssignment() - returns the number of submission files removed."""
    assignment = get_assignment_or_404(db, assignment_id)
    ensure_can_manage(user, assignment)
    submissions = list(db.scalars(select(Submission).where(Submission.assignment_id == assignment_id)).unique())
    if submissions and not force:
        raise ConflictError(
            f"This assignment has {len(submissions)} submission(s). Delete with force=true to remove them and their files.",
            code="HAS_SUBMISSIONS",
        )

    storage = get_storage_service()
    removed = 0
    for submission in submissions:
        try:
            storage.delete(submission.storage_path)
            removed += 1
        except StorageError:
            # Orphaned objects can be cleaned by a storage lifecycle rule; never block the delete.
            logger.warning("Could not delete object %s", submission.storage_path)
        db.delete(submission)
    db.delete(assignment)
    record_audit(db, "ASSIGNMENT_DELETED", user=user, entity_type="assignment", entity_id=assignment_id,
                 details={"title": assignment.title, "submissions_removed": len(submissions)}, request=request)
    db.commit()
    return removed


def get_assignments(db: Session, user: User, course_id: int | None = None) -> list[AssignmentOut]:
    """getAssignments() - role aware."""
    query = select(Assignment).order_by(Assignment.deadline)

    if user.role == Role.STUDENT.value:
        course_ids = course_service.enrolled_course_ids(db, user.user_id)
        query = query.where(Assignment.course_id.in_(course_ids))
        if course_id is not None:
            query = query.where(Assignment.course_id == course_id)
        assignments = list(db.scalars(query).unique())
        my_subs = {
            s.assignment_id: s
            for s in db.scalars(
                select(Submission).where(
                    Submission.student_id == user.user_id,
                    Submission.assignment_id.in_([a.assignment_id for a in assignments]),
                )
            ).unique()
        }
        return [
            serialize_assignment(a, my_submission=my_subs.get(a.assignment_id), include_my_status=True)
            for a in assignments
        ]

    managed = course_service.managed_course_ids(db, user)
    if managed is not None:
        query = query.where(Assignment.course_id.in_(managed))
    if course_id is not None:
        query = query.where(Assignment.course_id == course_id)
    assignments = list(db.scalars(query).unique())
    sub_counts = _submission_counts(db, [a.assignment_id for a in assignments])
    enrolled = _enrolled_counts(db, list({a.course_id for a in assignments}))
    return [
        serialize_assignment(
            a, submission_count=sub_counts.get(a.assignment_id, 0), enrolled_count=enrolled.get(a.course_id, 0)
        )
        for a in assignments
    ]


def get_assignment_by_id(db: Session, user: User, assignment_id: int) -> AssignmentOut:
    """getAssignmentById()"""
    assignment = get_assignment_or_404(db, assignment_id)
    ensure_can_view(db, user, assignment)
    if user.role == Role.STUDENT.value:
        mine = db.scalar(
            select(Submission).where(Submission.assignment_id == assignment_id, Submission.student_id == user.user_id)
        )
        return serialize_assignment(assignment, my_submission=mine, include_my_status=True)
    return serialize_assignment(
        assignment,
        submission_count=_submission_counts(db, [assignment_id]).get(assignment_id, 0),
        enrolled_count=_enrolled_counts(db, [assignment.course_id]).get(assignment.course_id, 0),
    )
