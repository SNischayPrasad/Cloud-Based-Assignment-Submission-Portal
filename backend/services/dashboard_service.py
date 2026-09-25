"""
Dashboard queries.

Counts are computed in the DATABASE with aggregate queries
(COUNT / GROUP BY / COUNT DISTINCT) instead of loading every row into
Python - this is what keeps dashboards fast as data grows. The indexes
on submissions(assignment_id, submission_status), submissions(student_id)
and assignments(course_id, deadline) exist for exactly these queries.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import Assignment, Course, Enrollment, Submission, SubmissionStatus, User
from backend.services import course_service
from backend.utils import time_utils


def _preview(text: str | None, length: int = 180) -> str | None:
    if not text:
        return text
    return text if len(text) <= length else text[: length - 1].rstrip() + "…"


def student_dashboard(db: Session, student: User) -> dict:
    now = time_utils.utcnow()
    course_ids = course_service.enrolled_course_ids(db, student.user_id)

    assignments = list(
        db.scalars(select(Assignment).where(Assignment.course_id.in_(course_ids)).order_by(Assignment.deadline)).unique()
    )
    submissions = {
        s.assignment_id: s
        for s in db.scalars(select(Submission).where(Submission.student_id == student.user_id)).unique()
    }
    mine = [submissions[a.assignment_id] for a in assignments if a.assignment_id in submissions]
    not_submitted = [a for a in assignments if a.assignment_id not in submissions]
    graded = [s for s in mine if s.submission_status == SubmissionStatus.GRADED.value]

    upcoming = [
        {
            "assignment_id": a.assignment_id,
            "title": a.title,
            "course_code": a.course.course_code,
            "deadline": a.deadline,
            "max_marks": a.max_marks,
        }
        for a in not_submitted
        if a.deadline > now
    ][:5]

    recent_feedback = [
        {
            "submission_id": s.submission_id,
            "assignment_id": s.assignment_id,
            "assignment_title": s.assignment.title,
            "course_code": s.assignment.course.course_code,
            "marks": s.marks,
            "max_marks": s.assignment.max_marks,
            "feedback_preview": _preview(s.feedback),
            "graded_at": s.graded_at,
        }
        for s in sorted(graded, key=lambda s: s.graded_at, reverse=True)[:5]
    ]

    percentages = [s.marks / s.assignment.max_marks * 100 for s in graded if s.marks is not None]
    return {
        "student_name": student.name,
        "stats": {
            "courses": len(course_ids),
            "total_assignments": len(assignments),
            "pending_assignments": len(not_submitted),
            "overdue_assignments": sum(1 for a in not_submitted if a.deadline < now),
            "submitted_assignments": len(mine),
            "late_assignments": sum(1 for s in mine if s.is_late),
            "graded_assignments": len(graded),
            "average_percentage": round(sum(percentages) / len(percentages), 1) if percentages else None,
        },
        "upcoming_deadlines": upcoming,
        "recent_feedback": recent_feedback,
    }


def teacher_dashboard(db: Session, user: User) -> dict:
    now = time_utils.utcnow()
    managed = course_service.managed_course_ids(db, user)  # None -> admin sees all

    def scope_assignments(query):
        return query if managed is None else query.where(Assignment.course_id.in_(managed))

    total_courses = len(managed) if managed is not None else db.scalar(select(func.count(Course.course_id)))
    total_assignments = db.scalar(scope_assignments(select(func.count(Assignment.assignment_id))))

    students_q = select(func.count(func.distinct(Enrollment.student_id)))
    if managed is not None:
        students_q = students_q.where(Enrollment.course_id.in_(managed))
    total_students = db.scalar(students_q)

    # SELECT submission_status, COUNT(*) ... GROUP BY submission_status
    status_counts = dict(
        db.execute(
            scope_assignments(
                select(Submission.submission_status, func.count(Submission.submission_id))
                .join(Assignment, Assignment.assignment_id == Submission.assignment_id)
            ).group_by(Submission.submission_status)
        ).all()
    )
    late_count = db.scalar(
        scope_assignments(
            select(func.count(Submission.submission_id))
            .join(Assignment, Assignment.assignment_id == Submission.assignment_id)
            .where(Submission.is_late.is_(True))
        )
    )

    recent = db.scalars(
        scope_assignments(
            select(Submission).join(Assignment, Assignment.assignment_id == Submission.assignment_id)
        )
        .order_by(Submission.submitted_at.desc())
        .limit(6)
    ).unique()
    recent_uploads = [
        {
            "submission_id": s.submission_id,
            "assignment_id": s.assignment_id,
            "assignment_title": s.assignment.title,
            "course_code": s.assignment.course.course_code,
            "student_name": s.student.name,
            "file_name": s.file_name,
            "submitted_at": s.submitted_at,
            "submission_status": s.submission_status,
            "is_late": s.is_late,
        }
        for s in recent
    ]

    upcoming_assignments = list(
        db.scalars(
            scope_assignments(select(Assignment).where(Assignment.deadline > now)).order_by(Assignment.deadline).limit(5)
        ).unique()
    )
    ids = [a.assignment_id for a in upcoming_assignments]
    sub_counts = dict(
        db.execute(
            select(Submission.assignment_id, func.count(Submission.submission_id))
            .where(Submission.assignment_id.in_(ids))
            .group_by(Submission.assignment_id)
        ).all()
    ) if ids else {}
    enrolled = dict(
        db.execute(
            select(Enrollment.course_id, func.count(Enrollment.enrollment_id))
            .where(Enrollment.course_id.in_({a.course_id for a in upcoming_assignments}))
            .group_by(Enrollment.course_id)
        ).all()
    ) if ids else {}
    upcoming = [
        {
            "assignment_id": a.assignment_id,
            "title": a.title,
            "course_code": a.course.course_code,
            "deadline": a.deadline,
            "submissions": sub_counts.get(a.assignment_id, 0),
            "enrolled": enrolled.get(a.course_id, 0),
        }
        for a in upcoming_assignments
    ]

    submitted = status_counts.get(SubmissionStatus.SUBMITTED.value, 0)
    late_pending = status_counts.get(SubmissionStatus.LATE.value, 0)
    graded = status_counts.get(SubmissionStatus.GRADED.value, 0)
    return {
        "teacher_name": user.name,
        "stats": {
            "courses": total_courses or 0,
            "total_assignments": total_assignments or 0,
            "total_students": total_students or 0,
            "total_submissions": submitted + late_pending + graded,
            "pending_reviews": submitted + late_pending,
            "late_submissions": late_count or 0,
            "graded_submissions": graded,
        },
        "recent_uploads": recent_uploads,
        "upcoming_deadlines": upcoming,
    }
