"""
Shared pytest fixtures.

Tests run against an isolated temporary SQLite database and a temporary
local storage folder, so they never touch your real data and need no
cloud account. Environment variables are set BEFORE the app is imported.
"""

import os
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="portal-tests-"))
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "SECRET_KEY": "test-secret-key-only-for-automated-tests-0123456789",
        "DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}",
        "STORAGE_PROVIDER": "local",
        "LOCAL_STORAGE_DIR": str(_TMP / "storage"),
        "PUBLIC_API_URL": "http://testserver",
        "RATE_LIMIT_PER_MINUTE": "1000",
        "MAX_UPLOAD_MB": "5",
        "ALLOWED_FILE_TYPES": "pdf,docx,zip,png,txt",
        "ALLOW_LATE_SUBMISSIONS": "true",
        "ALLOW_RESUBMISSION": "true",
        "LOG_LEVEL": "WARNING",
        "BCRYPT_ROUNDS": "4",  # minimum cost: keeps the suite fast (production uses 12)
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import app  # noqa: E402
from backend.middleware.rate_limit import auth_rate_limiter  # noqa: E402
from backend.models import Course, Enrollment, User  # noqa: E402
from backend.utils import time_utils  # noqa: E402
from backend.utils.pdf_builder import build_pdf  # noqa: E402
from cloud.auth_service import hash_password  # noqa: E402
from cloud.database_service import drop_all, get_session_factory, init_db  # noqa: E402

PASSWORD = "Password123"
_PASSWORD_HASH = hash_password(PASSWORD)  # hash once - bcrypt is slow on purpose


@pytest.fixture(autouse=True)
def fresh_state():
    """Every test starts with empty tables, empty storage and no rate-limit history."""
    drop_all()
    init_db()
    storage_dir = _TMP / "storage"
    shutil.rmtree(storage_dir, ignore_errors=True)
    storage_dir.mkdir(parents=True, exist_ok=True)
    auth_rate_limiter.reset()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = get_session_factory()()
    yield session
    session.close()


def create_user(db, name: str, email: str, role: str) -> User:
    user = User(name=name, email=email, role=role, password_hash=_PASSWORD_HASH)
    db.add(user)
    db.commit()
    return user


def login(client, email: str, password: str = PASSWORD) -> dict:
    response = client.post("/api/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def people(db, client):
    """Dummy users + one course taught by `teacher` with two enrolled students."""
    teacher = create_user(db, "Dr. Test Teacher", "teacher@test.dev", "teacher")
    other_teacher = create_user(db, "Other Teacher", "other.teacher@test.dev", "teacher")
    student = create_user(db, "Student One", "student1@test.dev", "student")
    other_student = create_user(db, "Student Two", "student2@test.dev", "student")
    admin = create_user(db, "Admin", "admin@test.dev", "admin")

    course = Course(course_code="CC401", course_name="Cloud Computing", description="", teacher_id=teacher.user_id, join_code="JOIN01")
    db.add(course)
    db.commit()
    db.add_all([
        Enrollment(course_id=course.course_id, student_id=student.user_id),
        Enrollment(course_id=course.course_id, student_id=other_student.user_id),
    ])
    db.commit()

    return {
        "course_id": course.course_id,
        "teacher": login(client, teacher.email),
        "other_teacher": login(client, other_teacher.email),
        "student": login(client, student.email),
        "other_student": login(client, other_student.email),
        "admin": login(client, admin.email),
        "student_id": student.user_id,
    }


def future(hours: float = 24) -> str:
    return (time_utils.utcnow() + timedelta(hours=hours)).isoformat()


@pytest.fixture
def make_assignment(client, people):
    def _make(**overrides):
        payload = {
            "course_id": people["course_id"],
            "title": "Cloud Architecture Report",
            "description": "Explain a three-tier architecture.",
            "deadline": future(24),
            "max_marks": 20,
            "allowed_file_types": ["pdf", "docx"],
            "max_file_size_mb": 2,
        }
        payload.update(overrides)
        response = client.post("/api/assignments", json=payload, headers=people["teacher"])
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def pdf_bytes():
    return build_pdf(["Test submission", "Cloud Computing"])


def upload(client, assignment_id: int, headers: dict, content: bytes, filename: str = "report.pdf",
           content_type: str = "application/pdf", extra_headers: dict | None = None):
    all_headers = dict(headers)
    if extra_headers:
        all_headers.update(extra_headers)
    return client.post(
        f"/api/assignments/{assignment_id}/submit",
        files={"file": (filename, content, content_type)},
        headers=all_headers,
    )


@pytest.fixture
def shift_clock(monkeypatch):
    """Move the server clock forward to simulate submitting after the deadline."""

    def _shift(hours: float):
        real = time_utils.utcnow
        monkeypatch.setattr(time_utils, "utcnow", lambda: real() + timedelta(hours=hours))

    return _shift


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TMP, ignore_errors=True)
