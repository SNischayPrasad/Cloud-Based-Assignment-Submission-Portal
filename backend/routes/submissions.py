"""SUBMISSION, FEEDBACK and FILE-DOWNLOAD endpoints."""

from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.middleware.auth import get_current_user, require_student, require_teacher
from backend.models import User
from backend.schemas.submission import DownloadOut, FeedbackOut, GradeRequest, SubmissionOut
from backend.services import grading_service, submission_service
from cloud.database_service import get_db

router = APIRouter(prefix="/api/submissions", tags=["Submissions & Feedback"])


@router.get("/me", response_model=list[SubmissionOut], summary="My submissions (student)")
def my_submissions(user: User = Depends(require_student), db: Session = Depends(get_db)):
    return submission_service.get_my_submissions(db, user)


@router.get("/{submission_id}", response_model=SubmissionOut, summary="Submission details (owner student or course teacher)")
def get_submission(submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return submission_service.get_submission(db, user, submission_id)


@router.post("/{submission_id}/grade", response_model=SubmissionOut, summary="Enter marks and feedback (course teacher)")
def grade_submission(
    submission_id: int,
    data: GradeRequest,
    request: Request,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return grading_service.grade_submission(db, user, submission_id, data, request)


@router.get("/{submission_id}/feedback", response_model=FeedbackOut, summary="Marks and feedback for a submission")
def get_feedback(submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return grading_service.get_submission_feedback(db, user, submission_id)


@router.get("/{submission_id}/download", response_model=DownloadOut, summary="Get a short-lived signed URL for the file")
def download_submission(
    submission_id: int,
    request: Request,
    disposition: Literal["attachment", "inline"] = Query(default="attachment", description="inline = open in browser"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return submission_service.get_download(db, user, submission_id, disposition, request)
