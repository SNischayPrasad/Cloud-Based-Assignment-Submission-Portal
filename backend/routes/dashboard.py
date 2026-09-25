"""DASHBOARD endpoints - one aggregated call per dashboard page."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.middleware.auth import require_student, require_teacher
from backend.models import User
from backend.services import dashboard_service
from cloud.database_service import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboards"])


@router.get("/student", summary="Student dashboard statistics")
def student_dashboard(user: User = Depends(require_student), db: Session = Depends(get_db)):
    return dashboard_service.student_dashboard(db, user)


@router.get("/teacher", summary="Teacher dashboard statistics (admin: whole portal)")
def teacher_dashboard(user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return dashboard_service.teacher_dashboard(db, user)
