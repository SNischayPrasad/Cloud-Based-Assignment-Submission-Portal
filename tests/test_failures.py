"""TC-22, TC-23: cloud storage failure, database failure, health checks."""

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.models import Submission
from backend.utils import retry
from cloud.storage_service import LocalStorageService, StorageError, get_storage_service
from tests.conftest import upload


def _stored_files() -> list:
    storage = get_storage_service()
    return [p for p in storage.root.rglob("*") if p.is_file() and not p.name.startswith(".")]


def test_tc22_storage_failure_returns_503_and_saves_nothing(client, db, people, make_assignment, pdf_bytes, monkeypatch):
    assignment = make_assignment()
    monkeypatch.setattr(retry.time, "sleep", lambda _s: None)  # skip backoff delays in tests

    calls = {"count": 0}

    def broken_upload(self, path, data, content_type):
        calls["count"] += 1
        raise StorageError("simulated outage")

    monkeypatch.setattr(LocalStorageService, "upload", broken_upload)
    response = upload(client, assignment["assignment_id"], people["student"], pdf_bytes)

    assert response.status_code == 503
    assert response.json()["code"] == "STORAGE_UNAVAILABLE"
    assert calls["count"] == 3  # retried with backoff before giving up
    assert db.scalar(select(func.count(Submission.submission_id))) == 0


def test_transient_storage_failure_is_retried(client, people, make_assignment, pdf_bytes, monkeypatch):
    assignment = make_assignment()
    monkeypatch.setattr(retry.time, "sleep", lambda _s: None)
    real_upload = LocalStorageService.upload
    calls = {"count": 0}

    def flaky_upload(self, path, data, content_type):
        calls["count"] += 1
        if calls["count"] == 1:
            raise StorageError("temporary network blip")
        return real_upload(self, path, data, content_type)

    monkeypatch.setattr(LocalStorageService, "upload", flaky_upload)
    response = upload(client, assignment["assignment_id"], people["student"], pdf_bytes)
    assert response.status_code == 201
    assert calls["count"] == 2


def test_tc23_database_failure_after_upload_cleans_up_file(client, people, make_assignment, pdf_bytes, monkeypatch):
    assignment = make_assignment()
    real_commit = Session.commit

    def failing_commit(self):
        # The service flushes first, so the pending Submission is already in the identity map.
        if any(isinstance(obj, Submission) for obj in self.identity_map.values()):
            raise OperationalError("COMMIT", {}, Exception("simulated database outage"))
        return real_commit(self)

    monkeypatch.setattr(Session, "commit", failing_commit)
    response = upload(client, assignment["assignment_id"], people["student"], pdf_bytes)

    assert response.status_code == 503
    assert response.json()["code"] == "DATABASE_UNAVAILABLE"
    assert _stored_files() == []  # compensation removed the orphaned object


def test_database_down_on_read_returns_503(client, people, monkeypatch):
    def broken_execute(self, *args, **kwargs):
        raise OperationalError("SELECT", {}, Exception("connection refused"))

    headers = people["student"]
    monkeypatch.setattr(Session, "execute", broken_execute)
    response = client.get("/api/dashboard/student", headers=headers)
    assert response.status_code == 503
    assert response.json()["code"] == "DATABASE_UNAVAILABLE"


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["ok"] is True
    assert body["checks"]["object_storage"]["provider"] == "local"
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_health_reports_degraded_storage(client, monkeypatch):
    monkeypatch.setattr(LocalStorageService, "health_check", lambda self: False)
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
