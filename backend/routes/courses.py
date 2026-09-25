"""COURSE endpoints: list/create courses, join by code, roster management."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.middleware.auth import get_current_user, require_student, require_teacher
from backend.models import User
from backend.schemas.course import CourseCreate, CourseOut, EnrollStudentRequest, JoinCourseRequest, RosterStudent
from backend.services import course_service
from cloud.database_service import get_db

router = APIRouter(prefix="/api/courses", tags=["Courses"])


@router.get("", response_model=list[CourseOut], summary="Courses I teach / I am enrolled in (admin: all)")
def list_courses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return course_service.list_courses(db, user)


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED, summary="Create a course (teacher/admin)")
def create_course(data: CourseCreate, request: Request, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return course_service.create_course(db, user, data, request)


@router.post("/join", response_model=CourseOut, status_code=status.HTTP_201_CREATED, summary="Join a course with its join code (student)")
def join_course(data: JoinCourseRequest, request: Request, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return course_service.join_course(db, user, data.join_code, request)


@router.get("/{course_id}/students", response_model=list[RosterStudent], summary="Course roster (course teacher)")
def roster(course_id: int, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return course_service.list_roster(db, user, course_id)


@router.post(
    "/{course_id}/students",
    response_model=RosterStudent,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a registered student by email (course teacher)",
)
def enroll_student(
    course_id: int,
    data: EnrollStudentRequest,
    request: Request,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return course_service.enroll_student_by_email(db, user, course_id, data.email, request)
