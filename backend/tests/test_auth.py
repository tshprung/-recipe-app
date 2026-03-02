"""Tests for user registration and login."""
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from app import models
from tests.conftest import TestSessionLocal


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


def test_register_sends_verification_email(client):
    with patch("app.routers.auth.send_verification_email") as mock_send:
        r = client.post(
            "/api/auth/register",
            json={"email": "verify@example.com", "password": "mypassword"},
        )
    assert r.status_code == 201
    data = r.json()
    # Email function called with user email and some token
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert args[0] == "verify@example.com"
    assert isinstance(args[1], str) and args[1]


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


def test_unverified_user_cannot_transform_recipe(client):
    # Register a fresh, unverified user (fixture auto-verifies only SAMPLE_EMAIL)
    r = client.post(
        "/api/auth/register",
        json={"email": "unverified@example.com", "password": "mypassword"},
    )
    assert r.status_code == 201

    # Login as that user
    r = client.post(
        "/api/auth/login",
        json={"email": "unverified@example.com", "password": "mypassword"},
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to create a recipe – must be blocked until verified
    r = client.post(
        "/api/recipes/",
        json={"raw_input": "מרק"},
        headers=headers,
    )
    assert r.status_code == 403
    assert "Zweryfikuj swój email" in r.json()["detail"]


def test_verified_user_can_transform_up_to_limit(client, auth_headers, registered_user):
    # Set a small limit for this user
    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == registered_user["email"]).first()
        user.transformations_limit = 2
        user.transformations_used = 0
        db.commit()
    finally:
        db.close()

    # First two transformations succeed
    for _ in range(2):
        r = client.post(
            "/api/recipes/",
            json={"raw_input": "מרק"},
            headers=auth_headers,
        )
        assert r.status_code == 201

    # Third transformation hits the quota
    r = client.post(
        "/api/recipes/",
        json={"raw_input": "מרk"},
        headers=auth_headers,
    )
    assert r.status_code == 402
    assert "Wykorzystałeś limit darmowych przepisów" in r.json()["detail"]


def test_failed_logins_lead_to_lockout(client, registered_user):
    # 4 failed attempts -> still 401
    for _ in range(4):
        r = client.post(
            "/api/auth/login",
            json={"email": registered_user["email"], "password": "wrong"},
        )
        assert r.status_code == 401

    # 5th failed attempt triggers lockout (still 401 on this request)
    r = client.post(
        "/api/auth/login",
        json={"email": registered_user["email"], "password": "wrong"},
    )
    assert r.status_code == 401

    # Subsequent attempt within lockout window returns 403 with lockout message
    r = client.post(
        "/api/auth/login",
        json={"email": registered_user["email"], "password": "securepassword"},
    )
    assert r.status_code == 403
    assert "Konto zablokowane" in r.json()["detail"]
