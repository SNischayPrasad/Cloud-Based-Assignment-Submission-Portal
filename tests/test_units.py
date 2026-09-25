"""Unit tests for pure helpers (no HTTP)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.services.deadline_policy import evaluate_submission_time
from backend.utils.errors import ForbiddenError, PayloadTooLargeError, UnsupportedFileError, ValidationFailed
from backend.utils.validators import normalize_file_types, sanitize_filename, validate_upload
from cloud.auth_service import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hashing():
    hashed = hash_password("Secret123")
    assert hashed != "Secret123"
    assert verify_password("Secret123", hashed)
    assert not verify_password("secret123", hashed)


def test_jwt_round_trip():
    token, jti, _ = create_access_token(7, "teacher")
    claims = decode_access_token(token)
    assert claims["sub"] == "7" and claims["role"] == "teacher" and claims["jti"] == jti


def test_sanitize_filename():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Users\\me\\My Report (final).pdf") == "My Report (final).pdf"
    assert sanitize_filename("bad<>name?.pdf") == "bad__name_.pdf"
    assert sanitize_filename("") == "file"


def test_normalize_file_types():
    assert normalize_file_types("PDF, .docx, pdf", ["pdf", "docx"]) == ["pdf", "docx"]
    with pytest.raises(ValidationFailed):
        normalize_file_types("exe", ["pdf"])
    with pytest.raises(ValidationFailed):
        normalize_file_types("", ["pdf"])


def test_validate_upload():
    assert validate_upload("a.pdf", b"%PDF-1.7 ...", ["pdf"], 1) == ("pdf", "application/pdf")
    with pytest.raises(UnsupportedFileError):
        validate_upload("a.exe", b"MZ", ["pdf"], 1)
    with pytest.raises(UnsupportedFileError):
        validate_upload("a.pdf", b"MZ fake", ["pdf"], 1)
    with pytest.raises(PayloadTooLargeError):
        validate_upload("a.pdf", b"%PDF-" + b"0" * (1024 * 1024), ["pdf"], 1)
    with pytest.raises(UnsupportedFileError):
        validate_upload("notes.txt", b"\x00\x01binary", ["txt"], 1)


@pytest.mark.parametrize(
    "offset_minutes, allow_late, expected",
    [(-1, False, ("SUBMITTED", False)), (0, False, ("SUBMITTED", False)), (1, True, ("LATE", True))],
)
def test_deadline_policy(offset_minutes, allow_late, expected):
    deadline = datetime(2026, 9, 30, 18, 30, tzinfo=timezone.utc)
    assignment = SimpleNamespace(deadline=deadline, allow_late_submission=allow_late)
    assert evaluate_submission_time(assignment, deadline + timedelta(minutes=offset_minutes)) == expected


def test_deadline_policy_blocks_late_when_disabled():
    deadline = datetime(2026, 9, 30, 18, 30, tzinfo=timezone.utc)
    assignment = SimpleNamespace(deadline=deadline, allow_late_submission=False)
    with pytest.raises(ForbiddenError):
        evaluate_submission_time(assignment, deadline + timedelta(seconds=1))


def test_deadline_is_timezone_safe():
    # 18:30 UTC is 00:00 the next day in India (UTC+05:30) - the same instant.
    deadline = datetime(2026, 9, 30, 18, 30, tzinfo=timezone.utc)
    ist = timezone(timedelta(hours=5, minutes=30))
    assignment = SimpleNamespace(deadline=deadline, allow_late_submission=True)
    assert evaluate_submission_time(assignment, datetime(2026, 10, 1, 0, 0, tzinfo=ist))[0] == "SUBMITTED"
    assert evaluate_submission_time(assignment, datetime(2026, 10, 1, 0, 1, tzinfo=ist))[0] == "LATE"
