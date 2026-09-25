"""
ASSIGNMENT endpoints (+ submit and teacher submission list, which are
nested under an assignment).
"""

from fastapi import APIRouter, Depends, File, Header, Query, Request, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.middleware.auth import get_current_user, require_student, require_teacher
from backend.models import User
from backend.schemas.assignment import AssignmentCreate, AssignmentOut, AssignmentUpdate
from backend.schemas.submission import AssignmentSubmissionsOut, SubmitResult
from backend.services import assignment_service, submission_service
from cloud.database_service import get_db

router = APIRouter(prefix="/api/assignments", tags=["Assignments"])


@router.post("", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED, summary="Create assignment (teacher)")
def create_assignment(
    data: AssignmentCreate, request: Request, user: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    return assignment_service.create_assignment(db, user, data, request)


@router.get("", response_model=list[AssignmentOut], summary="List assignments visible to the current user")
def list_assignments(
    course_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return assignment_service.get_assignments(db, user, course_id)


@router.get("/{assignment_id}", response_model=AssignmentOut, summary="Assignment details")
def get_assignment(assignment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return assignment_service.get_assignment_by_id(db, user, assignment_id)


@router.put("/{assignment_id}", response_model=AssignmentOut, summary="Update assignment (course teacher)")
def update_assignment(
    assignment_id: int,
    data: AssignmentUpdate,
    request: Request,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return assignment_service.update_assignment(db, user, assignment_id, data, request)


@router.delete("/{assignment_id}", summary="Delete assignment (course teacher)")
def delete_assignment(
    assignment_id: int,
    request: Request,
    force: bool = Query(default=False, description="Also delete existing submissions and their files"),
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    removed = assignment_service.delete_assignment(db, user, assignment_id, force, request)
    return {"message": "Assignment deleted.", "files_removed": removed}


@router.post(
    "/{assignment_id}/submit",
    response_model=SubmitResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload (or re-upload) a submission file (student)",
)
async def submit_assignment(
    assignment_id: int,
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="The assignment file"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=100),
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    # Read at most (portal limit + 1 byte): enough to detect "too large"
    # without letting a huge upload exhaust server memory.
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    await file.close()

    submission, replayed, resubmitted = await run_in_threadpool(
        submission_service.submit_assignment,
        db, user, assignment_id, file.filename or "", data, idempotency_key, request,
    )
    if replayed:
        response.status_code = status.HTTP_200_OK
        message = "This upload was already received - returning the saved submission."
    elif resubmitted:
        response.status_code = status.HTTP_200_OK
        message = "Resubmission received. Your previous file was replaced."
    else:
        message = "Submission received."
    if submission.is_late and not replayed:
        message += " It was recorded as LATE because the deadline had passed."
    return SubmitResult(submission=submission_service.serialize_submission(submission), message=message, replayed=replayed)


@router.get(
    "/{assignment_id}/submissions",
    response_model=AssignmentSubmissionsOut,
    summary="All students and their submission status for an assignment (course teacher)",
)
def list_assignment_submissions(assignment_id: int, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return submission_service.list_assignment_submissions(db, user, assignment_id)
