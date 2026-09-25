"""TC-06, TC-07 and assignment validation / ownership rules."""

from datetime import timedelta

from backend.utils import time_utils
from tests.conftest import future


def test_tc06_teacher_creates_assignment(make_assignment):
    assignment = make_assignment(allowed_file_types="PDF, .docx")
    assert assignment["title"] == "Cloud Architecture Report"
    assert assignment["allowed_file_types"] == ["pdf", "docx"]  # normalized
    assert assignment["course_code"] == "CC401"
    assert assignment["allow_late_submission"] is True  # portal default
    assert assignment["enrolled_count"] == 2


def test_tc07_student_views_assignment(client, people, make_assignment):
    assignment = make_assignment()
    listing = client.get("/api/assignments", headers=people["student"])
    assert listing.status_code == 200
    assert [a["assignment_id"] for a in listing.json()] == [assignment["assignment_id"]]
    assert listing.json()[0]["my_status"] == "NOT_SUBMITTED"

    detail = client.get(f"/api/assignments/{assignment['assignment_id']}", headers=people["student"])
    assert detail.status_code == 200
    assert detail.json()["description"] == "Explain a three-tier architecture."


def test_student_cannot_create_assignment(client, people):
    response = client.post(
        "/api/assignments",
        json={"course_id": people["course_id"], "title": "Hack", "deadline": future(), "max_marks": 10},
        headers=people["student"],
    )
    assert response.status_code == 403


def test_teacher_cannot_create_in_other_teachers_course(client, people):
    response = client.post(
        "/api/assignments",
        json={"course_id": people["course_id"], "title": "Not my course", "deadline": future(), "max_marks": 10},
        headers=people["other_teacher"],
    )
    assert response.status_code == 403


def test_assignment_validation(client, people):
    base = {"course_id": people["course_id"], "title": "Valid title", "deadline": future(), "max_marks": 10}
    past = dict(base, deadline=(time_utils.utcnow() - timedelta(hours=1)).isoformat())
    assert client.post("/api/assignments", json=past, headers=people["teacher"]).status_code == 400

    bad_type = dict(base, allowed_file_types=["exe"])
    assert client.post("/api/assignments", json=bad_type, headers=people["teacher"]).status_code == 400

    zero_marks = dict(base, max_marks=0)
    assert client.post("/api/assignments", json=zero_marks, headers=people["teacher"]).status_code == 422

    too_big = dict(base, max_file_size_mb=50)  # portal limit in tests is 5 MB
    assert client.post("/api/assignments", json=too_big, headers=people["teacher"]).status_code == 400

    short_title = dict(base, title="ab")
    assert client.post("/api/assignments", json=short_title, headers=people["teacher"]).status_code == 422


def test_update_assignment(client, people, make_assignment):
    assignment = make_assignment()
    new_deadline = future(48)
    response = client.put(
        f"/api/assignments/{assignment['assignment_id']}",
        json={"title": "Updated title", "deadline": new_deadline, "max_marks": 25},
        headers=people["teacher"],
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"
    assert response.json()["max_marks"] == 25

    forbidden = client.put(
        f"/api/assignments/{assignment['assignment_id']}", json={"title": "Nope"}, headers=people["other_teacher"]
    )
    assert forbidden.status_code == 403


def test_delete_assignment_requires_force_when_submissions_exist(client, people, make_assignment, pdf_bytes):
    from tests.conftest import upload

    assignment = make_assignment()
    assert upload(client, assignment["assignment_id"], people["student"], pdf_bytes).status_code == 201

    blocked = client.delete(f"/api/assignments/{assignment['assignment_id']}", headers=people["teacher"])
    assert blocked.status_code == 409

    forced = client.delete(f"/api/assignments/{assignment['assignment_id']}?force=true", headers=people["teacher"])
    assert forced.status_code == 200
    assert forced.json()["files_removed"] == 1
    assert client.get(f"/api/assignments/{assignment['assignment_id']}", headers=people["teacher"]).status_code == 404


def test_student_not_enrolled_cannot_see_assignment(client, db, people, make_assignment):
    from tests.conftest import create_user, login

    create_user(db, "Outsider", "outsider@test.dev", "student")
    outsider = login(client, "outsider@test.dev")
    assignment = make_assignment()
    assert client.get("/api/assignments", headers=outsider).json() == []
    assert client.get(f"/api/assignments/{assignment['assignment_id']}", headers=outsider).status_code == 403
