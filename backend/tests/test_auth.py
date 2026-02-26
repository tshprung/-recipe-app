"""Tests for user registration and login."""


def test_register_success(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "mypassword"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "new@example.com"
    assert "id" in data
    assert "password_hash" not in data  # never exposed


def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "pass"}
    client.post("/api/auth/register", json=payload)
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 409


def test_login_success(client, registered_user):
    r = client.post(
        "/api/auth/login",
        json={"email": "tester@example.com", "password": "securepassword"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, registered_user):
    r = client.post(
        "/api/auth/login",
        json={"email": "tester@example.com", "password": "wrongpassword"},
    )
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "any"},
    )
    assert r.status_code == 401


def test_protected_endpoint_without_token(client):
    r = client.get("/api/recipes/")
    assert r.status_code == 401


def test_jwt_token_is_usable(client, registered_user, auth_headers):
    r = client.get("/api/recipes/", headers=auth_headers)
    assert r.status_code == 200
