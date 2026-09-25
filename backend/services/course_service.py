"""Courses, enrollment and course-level access rules."""

import secrets

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Assignment, Course, Enrollment, Role, User
from backend.schemas.course import CourseCreate, CourseOut, RosterStudent
from backend.utils.audit import record_audit
from backend.utils.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailed

# No 0/O/1/I - easy to read aloud in class.
_JOIN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _new_join_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(_JOIN_ALPHABET) for _ in range(6))
        if db.scalar(select(Course.course_id).where(Course.join_code == code)) is None:
            return code


# ------------------------------------------------------------ access helpers
def managed_course_ids(db: Session, user: User) -> list[int] | None:
    """Courses a teacher manages. None means 'all courses' (admin)."""
    if user.role == Role.ADMIN.value:
        return None
    if user.role == Role.TEACHER.value:
        return list(db.scalars(select(Course.course_id).where(Course.teacher_id == user.user_id)))
    return []


def enrolled_course_ids(db: Session, student_id: int) -> list[int]:
    return list(db.scalars(select(Enrollment.course_id).where(Enrollment.student_id == student_id)))


def is_enrolled(db: Session, student_id: int, course_id: int) -> bool:
    return db.scalar(
        select(Enrollment.enrollment_id).where(Enrollment.student_id == student_id, Enrollment.course_id == course_id)
    ) is not None


def can_manage_course(user: User, course: Course) -> bool:
    return user.role == Role.ADMIN.value or (user.role == Role.TEACHER.value and course.teacher_id == user.user_id)


def get_course_for_manager(db: Session, user: User, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise NotFoundError("Course not found.")
    if not can_manage_course(user, course):
        raise ForbiddenError("You can only manage courses you teach.", code="COURSE_FORBIDDEN")
    return course


# ------------------------------------------------------------- serializers
def _counts(db: Session, course_ids: list[int]) -> tuple[dict[int, int], dict[int, int]]:
    if not course_ids:
        return {}, {}
    students = dict(
        db.execute(
            select(Enrollment.course_id, func.count(Enrollment.enrollment_id))
            .where(Enrollment.course_id.in_(course_ids))
            .group_by(Enrollment.course_id)
        ).all()
    )
    assignments = dict(
        db.execute(
            select(Assignment.course_id, func.count(Assignment.assignment_id))
            .where(Assignment.course_id.in_(course_ids))
            .group_by(Assignment.course_id)
        ).all()
    )
    return students, assignments


def serialize_course(course: Course, viewer: User, student_count: int, assignment_count: int) -> CourseOut:
    return CourseOut(
        course_id=course.course_id,
        course_code=course.course_code,
        course_name=course.course_name,
        description=course.description,
        teacher_id=course.teacher_id,
        teacher_name=course.teacher.name if course.teacher else "",
        join_code=course.join_code if can_manage_course(viewer, course) else None,
        student_count=student_count,
        assignment_count=assignment_count,
        created_at=course.created_at,
    )


# ------------------------------------------------------------------ actions
def list_courses(db: Session, user: User) -> list[CourseOut]:
    query = select(Course).order_by(Course.course_code)
    if user.role == Role.STUDENT.value:
        query = query.where(Course.course_id.in_(enrolled_course_ids(db, user.user_id)))
    elif user.role == Role.TEACHER.value:
        query = query.where(Course.teacher_id == user.user_id)
    courses = list(db.scalars(query).unique())
    students, assignments = _counts(db, [c.course_id for c in courses])
    return [
        serialize_course(c, user, students.get(c.course_id, 0), assignments.get(c.course_id, 0)) for c in courses
    ]


def create_course(db: Session, user: User, data: CourseCreate, request: Request | None = None) -> CourseOut:
    if user.role == Role.ADMIN.value:
        if data.teacher_id is None:
            raise ValidationFailed("teacher_id is required when an admin creates a course.")
        teacher = db.get(User, data.teacher_id)
        if teacher is None or teacher.role != Role.TEACHER.value:
            raise ValidationFailed("teacher_id must refer to an existing teacher account.")
        owner_id = teacher.user_id
    else:
        owner_id = user.user_id

    if db.scalar(select(Course.course_id).where(Course.course_code == data.course_code)) is not None:
        raise ConflictError(f"Course code {data.course_code} already exists.", code="COURSE_EXISTS")

    course = Course(
        course_code=data.course_code,
        course_name=data.course_name.strip(),
        description=data.description.strip(),
        teacher_id=owner_id,
        join_code=_new_join_code(db),
    )
    db.add(course)
    db.flush()
    record_audit(db, "COURSE_CREATED", user=user, entity_type="course", entity_id=course.course_id, request=request)
    db.commit()
    db.refresh(course)
    return serialize_course(course, user, 0, 0)


def join_course(db: Session, student: User, join_code: str, request: Request | None = None) -> CourseOut:
    course = db.scalar(select(Course).where(Course.join_code == join_code.strip().upper()))
    if course is None:
        raise NotFoundError("No course matches that join code. Check the code with your teacher.", code="BAD_JOIN_CODE")
    if is_enrolled(db, student.user_id, course.course_id):
        raise ConflictError(f"You are already enrolled in {course.course_code}.", code="ALREADY_ENROLLED")
    db.add(Enrollment(course_id=course.course_id, student_id=student.user_id))
    record_audit(db, "COURSE_JOINED", user=student, entity_type="course", entity_id=course.course_id, request=request)
    db.commit()
    students, assignments = _counts(db, [course.course_id])
    return serialize_course(course, student, students.get(course.course_id, 0), assignments.get(course.course_id, 0))


def enroll_student_by_email(db: Session, user: User, course_id: int, email: str, request: Request | None = None) -> RosterStudent:
    course = get_course_for_manager(db, user, course_id)
    student = db.scalar(select(User).where(User.email == email.lower()))
    if student is None or student.role != Role.STUDENT.value:
        raise NotFoundError("No student account uses that email. Ask the student to register first.")
    enrollment = Enrollment(course_id=course.course_id, student_id=student.user_id)
    db.add(enrollment)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(f"{student.name} is already enrolled in {course.course_code}.") from exc
    record_audit(db, "STUDENT_ENROLLED", user=user, entity_type="course", entity_id=course.course_id,
                 details={"student_id": student.user_id}, request=request)
    db.commit()
    return RosterStudent(student_id=student.user_id, name=student.name, email=student.email, enrolled_at=enrollment.enrolled_at)


def list_roster(db: Session, user: User, course_id: int) -> list[RosterStudent]:
    course = get_course_for_manager(db, user, course_id)
    rows = db.scalars(
        select(Enrollment).where(Enrollment.course_id == course.course_id)
    ).unique()
    roster = [
        RosterStudent(student_id=e.student_id, name=e.student.name, email=e.student.email, enrolled_at=e.enrolled_at)
        for e in rows
    ]
    return sorted(roster, key=lambda r: r.name.lower())
