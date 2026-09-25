"""TC-04, TC-05: role-based dashboards, courses, admin-only endpoints."""

from tests.conftest import upload


def test_tc04_student_dashboard_authorization(client, people, make_assignment, pdf_bytes):
    make_assignment(title="Assignment A")
    b = make_assignment(title="Assignment B")
    upload(client, b["assignment_id"], people["student"], pdf_bytes)

    response = client.get("/api/dashboard/student", headers=people["student"])
    assert response.status_code == 200
    stats = response.json()["stats"]
    assert stats["total_assignments"] == 2
    assert stats["pending_assignments"] == 1
    assert stats["submitted_assignments"] == 1
    assert len(response.json()["upcoming_deadlines"]) == 1

    # A student cannot open the teacher dashboard
    assert client.get("/api/dashboard/teacher", headers=people["student"]).status_code == 403


def test_tc05_teacher_dashboard_authorization(client, people, make_assignment, pdf_bytes):
    a = make_assignment()
    upload(client, a["assignment_id"], people["student"], pdf_bytes)

    response = client.get("/api/dashboard/teacher", headers=people["teacher"])
    assert response.status_code == 200
    stats = response.json()["stats"]
    assert stats["total_assignments"] == 1
    assert stats["total_students"] == 2
    assert stats["total_submissions"] == 1
    assert stats["pending_reviews"] == 1
    assert response.json()["recent_uploads"][0]["student_name"] == "Student One"

    # The other teacher sees none of it
    other = client.get("/api/dashboard/teacher", headers=people["other_teacher"]).json()["stats"]
    assert other["total_assignments"] == 0 and other["total_submissions"] == 0

    # A teacher cannot open the student dashboard
    assert client.get("/api/dashboard/student", headers=people["teacher"]).status_code == 403


def test_join_course_with_code(client, db, people):
    from tests.conftest import create_user, login

    create_user(db, "New Student", "new@test.dev", "student")
    headers = login(client, "new@test.dev")
    assert client.get("/api/courses", headers=headers).json() == []

    bad = client.post("/api/courses/join", json={"join_code": "WRONG1"}, headers=headers)
    assert bad.status_code == 404
    joined = client.post("/api/courses/join", json={"join_code": "join01"}, headers=headers)
    assert joined.status_code == 201
    assert joined.json()["course_code"] == "CC401"
    assert joined.json()["join_code"] is None  # students never see the join code
    assert client.post("/api/courses/join", json={"join_code": "JOIN01"}, headers=headers).status_code == 409


def test_teacher_creates_course_and_sees_join_code(client, people):
    response = client.post("/api/courses", json={"course_code": "ai201", "course_name": "Applied AI"}, headers=people["teacher"])
    assert response.status_code == 201
    assert response.json()["course_code"] == "AI201"
    assert len(response.json()["join_code"]) == 6
    assert client.post("/api/courses", json={"course_code": "X1", "course_name": "Hack"}, headers=people["student"]).status_code == 403


def test_admin_only_endpoints(client, people):
    assert client.get("/api/admin/users", headers=people["teacher"]).status_code == 403
    assert client.get("/api/admin/users", headers=people["student"]).status_code == 403
    users = client.get("/api/admin/users", headers=people["admin"])
    assert users.status_code == 200 and len(users.json()) == 5

    created = client.post(
        "/api/admin/users",
        json={"name": "New Teacher", "email": "nt@test.dev", "password": "Teacher123", "role": "teacher"},
        headers=people["admin"],
    )
    assert created.status_code == 201 and created.json()["role"] == "teacher"

    logs = client.get("/api/admin/audit-logs", headers=people["admin"]).json()
    assert any(entry["action"] == "USER_CREATED" for entry in logs)
    assert any(entry["action"] == "LOGIN_SUCCESS" for entry in logs)


def test_role_change_takes_effect_immediately(client, db, people):
    # The role is read from the database on every request, not trusted from the token.
    from backend.models import User

    student = db.get(User, people["student_id"])
    student.role = "teacher"
    db.commit()
    assert client.get("/api/dashboard/teacher", headers=people["student"]).status_code == 200
