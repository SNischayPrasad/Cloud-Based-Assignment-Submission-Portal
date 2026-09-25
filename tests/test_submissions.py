"""TC-08..TC-15, TC-21: uploads, validation, deadlines, resubmission, access, download."""

from urllib.parse import urlparse

from sqlalchemy import select

from backend.models import Submission
from cloud.storage_service import get_storage_service
from tests.conftest import upload


def test_tc08_valid_pdf_upload_and_tc11_on_time(client, db, people, make_assignment, pdf_bytes):
    assignment = make_assignment()
    response = upload(client, assignment["assignment_id"], people["student"], pdf_bytes)
    assert response.status_code == 201, response.text
    submission = response.json()["submission"]
    assert submission["submission_status"] == "SUBMITTED"
    assert submission["is_late"] is False
    assert submission["file_name"] == "report.pdf"
    assert submission["storage_path"].startswith(
        f"assignments/assignment_{assignment['assignment_id']:03d}/student_{people['student_id']:03d}/"
    )

    # File really is in object storage and matches byte-for-byte ...
    assert get_storage_service().download(submission["storage_path"]) == pdf_bytes
    # ... and the metadata row is in the database.
    row = db.scalar(select(Submission).where(Submission.submission_id == submission["submission_id"]))
    assert row is not None and row.file_size == len(pdf_bytes)


def test_tc09_invalid_extension(client, people, make_assignment):
    assignment = make_assignment()
    response = upload(client, assignment["assignment_id"], people["student"], b"MZ\x90\x00", "virus.exe", "application/octet-stream")
    assert response.status_code == 415


def test_renamed_file_rejected_by_content_check(client, people, make_assignment):
    assignment = make_assignment()
    response = upload(client, assignment["assignment_id"], people["student"], b"this is plain text, not a pdf", "fake.pdf")
    assert response.status_code == 415
    assert "does not match" in response.json()["detail"]


def test_tc10_oversized_file(client, people, make_assignment):
    assignment = make_assignment(max_file_size_mb=1)
    big = b"%PDF-1.4\n" + b"0" * (1024 * 1024 + 10)
    response = upload(client, assignment["assignment_id"], people["student"], big)
    assert response.status_code == 413


def test_empty_file_rejected(client, people, make_assignment):
    assignment = make_assignment()
    assert upload(client, assignment["assignment_id"], people["student"], b"").status_code == 400


def test_tc12_late_submission_recorded_as_late(client, people, make_assignment, pdf_bytes, shift_clock):
    assignment = make_assignment(allow_late_submission=True)
    shift_clock(hours=30)  # server clock is now past the 24h deadline
    response = upload(client, assignment["assignment_id"], people["student"], pdf_bytes)
    assert response.status_code == 201
    assert response.json()["submission"]["submission_status"] == "LATE"
    assert response.json()["submission"]["is_late"] is True
    assert "LATE" in response.json()["message"]


def test_late_submission_blocked_when_disabled(client, people, make_assignment, pdf_bytes, shift_clock):
    assignment = make_assignment(allow_late_submission=False)
    shift_clock(hours=30)
    response = upload(client, assignment["assignment_id"], people["student"], pdf_bytes)
    assert response.status_code == 403
    assert response.json()["code"] == "DEADLINE_PASSED"


def test_tc13_resubmission_replaces_file(client, people, make_assignment, pdf_bytes):
    assignment = make_assignment(allow_resubmission=True)
    first = upload(client, assignment["assignment_id"], people["student"], pdf_bytes).json()["submission"]
    second_bytes = pdf_bytes + b"\n% version 2"
    response = upload(client, assignment["assignment_id"], people["student"], second_bytes, "report_v2.pdf")
    assert response.status_code == 200
    second = response.json()["submission"]
    assert second["submission_id"] == first["submission_id"]
    assert second["attempt_number"] == 2
    assert second["file_name"] == "report_v2.pdf"
    storage = get_storage_service()
    assert storage.exists(second["storage_path"])
    assert not storage.exists(first["storage_path"])  # old object cleaned up


def test_duplicate_submission_blocked_when_resubmission_disabled(client, people, make_assignment, pdf_bytes):
    assignment = make_assignment(allow_resubmission=False)
    assert upload(client, assignment["assignment_id"], people["student"], pdf_bytes).status_code == 201
    response = upload(client, assignment["assignment_id"], people["student"], pdf_bytes)
    assert response.status_code == 409
    assert response.json()["code"] == "DUPLICATE_SUBMISSION"


def test_idempotent_retry_does_not_create_second_attempt(client, people, make_assignment, pdf_bytes):
    assignment = make_assignment()
    key = {"Idempotency-Key": "upload-7f3a"}
    first = upload(client, assignment["assignment_id"], people["student"], pdf_bytes, extra_headers=key)
    retry = upload(client, assignment["assignment_id"], people["student"], pdf_bytes, extra_headers=key)
    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json()["replayed"] is True
    assert retry.json()["submission"]["attempt_number"] == 1


def test_teacher_cannot_submit(client, people, make_assignment, pdf_bytes):
    assignment = make_assignment()
    assert upload(client, assignment["assignment_id"], people["teacher"], pdf_bytes).status_code == 403


def test_tc14_student_views_own_submissions(client, people, make_assignment, pdf_bytes):
    assignment = make_assignment()
    upload(client, assignment["assignment_id"], people["student"], pdf_bytes)
    mine = client.get("/api/submissions/me", headers=people["student"])
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert client.get("/api/submissions/me", headers=people["other_student"]).json() == []


def test_tc15_student_cannot_view_another_students_submission(client, people, make_assignment, pdf_bytes):
    assignment = make_assignment()
    submission_id = upload(client, assignment["assignment_id"], people["student"], pdf_bytes).json()["submission"]["submission_id"]
    for path in ("", "/feedback", "/download"):
        response = client.get(f"/api/submissions/{submission_id}{path}", headers=people["other_student"])
        assert response.status_code == 403, path


def test_tc21_file_retrieval_via_signed_url(client, people, make_assignment, pdf_bytes):
    assignment = make_assignment()
    submission_id = upload(client, assignment["assignment_id"], people["student"], pdf_bytes).json()["submission"]["submission_id"]

    for who in ("student", "teacher"):
        link = client.get(f"/api/submissions/{submission_id}/download", headers=people[who])
        assert link.status_code == 200
        url = urlparse(link.json()["url"])
        file_response = client.get(f"{url.path}?{url.query}")  # no auth header: the signature is the permission
        assert file_response.status_code == 200
        assert file_response.content == pdf_bytes
        assert "attachment" in file_response.headers["content-disposition"]


def test_tampered_or_expired_signed_url_rejected(client, people, make_assignment, pdf_bytes):
    assignment = make_assignment()
    submission_id = upload(client, assignment["assignment_id"], people["student"], pdf_bytes).json()["submission"]["submission_id"]
    url = urlparse(client.get(f"/api/submissions/{submission_id}/download", headers=people["student"]).json()["url"])

    tampered = url.query.replace("student_", "studenX_")
    assert client.get(f"{url.path}?{tampered}").status_code in (403, 404)

    expired = "&".join(
        "expires=1000" if part.startswith("expires=") else part for part in url.query.split("&")
    )
    assert client.get(f"{url.path}?{expired}").status_code == 403


def test_unauthenticated_download_rejected(client, people, make_assignment, pdf_bytes):
    assignment = make_assignment()
    submission_id = upload(client, assignment["assignment_id"], people["student"], pdf_bytes).json()["submission"]["submission_id"]
    assert client.get(f"/api/submissions/{submission_id}/download").status_code == 401
