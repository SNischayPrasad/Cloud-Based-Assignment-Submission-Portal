"""ADMIN endpoints: user management and audit logs."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from backend.middleware.auth import require_admin
from backend.models import User
from backend.schemas.user import AdminCreateUser, AdminUpdateUser, AuditLogOut, UserOut
from backend.services import user_service
from cloud.database_service import get_db

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserOut], summary="List users")
def list_users(role: str | None = Query(default=None), _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return user_service.list_users(db, role)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Create a user with any role")
def create_user(data: AdminCreateUser, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return user_service.create_user(db, admin, data, request)


@router.patch("/users/{user_id}", response_model=UserOut, summary="Change role / activate / deactivate")
def update_user(
    user_id: int, data: AdminUpdateUser, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    return user_service.update_user(db, admin, user_id, data, request)


@router.get("/audit-logs", response_model=list[AuditLogOut], summary="Recent security audit events")
def audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = Query(default=None),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_service.list_audit_logs(db, limit, action)
