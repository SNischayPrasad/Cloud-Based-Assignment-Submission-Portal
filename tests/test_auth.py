"""TC-01, TC-02, TC-03, TC-24, TC-25: registration, login, logout."""

from tests.conftest import PASSWORD, create_user, login


def test_tc01_student_registration(client):
    response = client.post(
        "/api/register",
        json={"name": "Aarav Sharma", "email": "Aarav@Portal.dev", "password": "Student123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "student"
    assert body["email"] == "aarav@portal.dev"  # normalized
    assert "password" not in body and "password_hash" not in body


def test_registration_cannot_escalate_role(client):
    response = client.post(
        "/api/register",
        json={"name": "Sneaky", "email": "sneaky@portal.dev", "password": "Student123", "role": "teacher"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "student"  # extra field ignored


def test_duplicate_email_rejected(client):
    payload = {"name": "Priya Nair", "email": "priya@portal.dev", "password": "Student123"}
    assert client.post("/api/register", json=payload).status_code == 201
    response = client.post("/api/register", json=payload)
    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_EXISTS"


def test_weak_password_rejected(client):
    response = client.post("/api/register", json={"name": "Weak", "email": "weak@portal.dev", "password": "short"})
    assert response.status_code == 422


def test_tc02_teacher_login(client, db):
    create_user(db, "Dr. Meera Iyer", "meera@portal.dev", "teacher")
    response = client.post("/api/login", json={"email": "meera@portal.dev", "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "teacher"
    assert body["expires_in"] > 0


def test_tc03_invalid_login(client, db):
    create_user(db, "Rahul", "rahul@portal.dev", "student")
    wrong_password = client.post("/api/login", json={"email": "rahul@portal.dev", "password": "WrongPass1"})
    unknown_email = client.post("/api/login", json={"email": "nobody@portal.dev", "password": "WrongPass1"})
    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    # Same message for both -> attackers cannot discover which emails exist.
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


def test_protected_route_requires_token(client):
    assert client.get("/api/assignments").status_code == 401
    assert client.get("/api/assignments", headers={"Authorization": "Bearer not-a-real-token"}).status_code == 401


def test_tc24_logout_and_tc25_protected_route_after_logout(client, db):
    create_user(db, "Sara", "sara@portal.dev", "student")
    headers = login(client, "sara@portal.dev")
    assert client.get("/api/me", headers=headers).status_code == 200

    response = client.post("/api/logout", headers=headers)
    assert response.status_code == 200

    after = client.get("/api/me", headers=headers)
    assert after.status_code == 401
    assert after.json()["code"] == "TOKEN_REVOKED"


def test_disabled_account_cannot_use_existing_token(client, db):
    user = create_user(db, "Temp", "temp@portal.dev", "student")
    headers = login(client, "temp@portal.dev")
    user.is_active = False
    db.commit()
    assert client.get("/api/me", headers=headers).status_code == 401


def test_login_rate_limited(client, db, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
    from backend.config import get_settings

    get_settings.cache_clear()
    try:
        codes = [client.post("/api/login", json={"email": "x@portal.dev", "password": "Wrong1234"}).status_code for _ in range(4)]
        assert codes[:3] == [401, 401, 401]
        assert codes[3] == 429
    finally:
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1000")
        get_settings.cache_clear()
