"""Tests for user registration, login, and verification."""
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from app import models
from tests.conftest import TestSessionLocal, MOCK_TRANSLATED


def test_register_success(client):
    with patch("app.routers.auth.send_verification_email"):
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
    payload = {"email": "dup@example.com", "password": "password8"}
    with patch("app.routers.auth.send_verification_email"):
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
    with patch("app.routers.auth.send_verification_email"):
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

    # First two transformations succeed (mock translation so we don't call OpenAI)
    with patch("app.routers.recipes.translate_recipe", return_value=MOCK_TRANSLATED):
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


def test_verify_email_marks_user_verified_and_clears_token(client):
    # Register a new user so they get a token
    with patch("app.routers.auth.send_verification_email"):
        r = client.post(
            "/api/auth/register",
            json={"email": "verify-me@example.com", "password": "mypassword"},
        )
    assert r.status_code == 201

    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == "verify-me@example.com").first()
        token = user.verification_token
        assert token is not None
    finally:
        db.close()

    # Call verify endpoint
    r = client.post(f"/api/auth/verify?token={token}")
    assert r.status_code == 200

    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == "verify-me@example.com").first()
        assert user.is_verified is True
        assert user.verification_token is None
        assert user.verification_token_expires is None
    finally:
        db.close()


def test_verify_email_handles_naive_expiry_datetime(client):
    # Register user and then override expiry to a naive datetime in the future
    with patch("app.routers.auth.send_verification_email"):
        r = client.post(
            "/api/auth/register",
            json={"email": "naive-expiry@example.com", "password": "mypassword"},
        )
    assert r.status_code == 201

    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == "naive-expiry@example.com").first()
        token = user.verification_token
        # Set a naive (tzinfo=None) expiry to simulate legacy data
        user.verification_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
    finally:
        db.close()

    # Verify should succeed and must not raise naive/aware TypeError
    r = client.post(f"/api/auth/verify?token={token}")
    assert r.status_code == 200

    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == "naive-expiry@example.com").first()
        assert user.is_verified is True
    finally:
        db.close()


def test_verify_email_rejects_expired_token(client):
    with patch("app.routers.auth.send_verification_email"):
        r = client.post(
            "/api/auth/register",
            json={"email": "expired@example.com", "password": "mypassword"},
        )
    assert r.status_code == 201

    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == "expired@example.com").first()
        token = user.verification_token
        # Set expiry in the past
        user.verification_token_expires = datetime.utcnow() - timedelta(hours=1)
        db.commit()
    finally:
        db.close()

    r = client.post(f"/api/auth/verify?token={token}")
    assert r.status_code == 400
    assert "Nieprawidłowy lub wygasły token" in r.json()["detail"]


def test_register_returns_503_when_verification_email_fails(client):
    with patch("app.routers.auth.send_verification_email") as mock_send:
        mock_send.side_effect = RuntimeError("Resend unavailable")
        r = client.post(
            "/api/auth/register",
            json={"email": "fail-email@example.com", "password": "mypassword"},
        )
    # User is created then we try to send email; send fails -> 503
    assert r.status_code == 503
    assert "email" in r.json().get("detail", "").lower() or "weryfikacyjn" in r.json().get("detail", "")


def test_resend_verification_returns_503_when_email_fails(client, registered_user, auth_headers):
    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == registered_user["email"]).first()
        user.is_verified = False
        db.commit()
    finally:
        db.close()

    with patch("app.routers.auth.send_verification_email") as mock_send:
        mock_send.side_effect = RuntimeError("Resend error")
        r = client.post("/api/auth/resend-verification", headers=auth_headers)
    assert r.status_code == 503


def test_resend_verification_503_includes_config_message(client, registered_user, auth_headers):
    """When Resend fails (e.g. 401), client gets 503 with message pointing to server config."""
    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == registered_user["email"]).first()
        user.is_verified = False
        db.commit()
    finally:
        db.close()

    with patch("app.routers.auth.send_verification_email") as mock_send:
        mock_send.side_effect = RuntimeError("RESEND_API_KEY is invalid or expired. Check your Resend dashboard.")
        r = client.post("/api/auth/resend-verification", headers=auth_headers)
    assert r.status_code == 503
    detail = r.json().get("detail", "")
    assert "RESEND" in detail or "konfigurację" in detail or "serwerze" in detail


def test_delete_me_requires_auth(client):
    r = client.delete("/api/users/me")
    assert r.status_code == 401


def test_delete_me_removes_user_and_recipes(client, auth_headers, recipe):
    """DELETE /api/users/me returns 204 and removes user and their recipes."""
    r = client.delete("/api/users/me", headers=auth_headers)
    assert r.status_code == 204

    # User and their recipes should be gone
    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == "tester@example.com").first()
        assert user is None
        recipe_count = db.query(models.Recipe).count()
        assert recipe_count == 0
    finally:
        db.close()
