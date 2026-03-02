"""Tests for admin upgrade endpoint and rate limiting."""
import os

import pytest
from fastapi.testclient import TestClient

from app import models
from tests.conftest import TestSessionLocal


def test_admin_upgrade_user_works_with_correct_token(client: TestClient, registered_user):
    r = client.post(
        "/api/admin/upgrade-user",
        json={"email": registered_user["email"], "new_limit": -1},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == registered_user["email"]
    assert data["new_limit"] == -1

    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == registered_user["email"]).first()
        assert user.transformations_limit == -1
        assert user.account_tier == "unlimited"
    finally:
        db.close()


def test_admin_upgrade_user_fails_with_wrong_token(client: TestClient, registered_user):
    r = client.post(
        "/api/admin/upgrade-user",
        json={"email": registered_user["email"], "new_limit": 10},
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert r.status_code == 401


@pytest.mark.skipif(os.getenv("TESTING") == "1", reason="Rate limiting disabled in test env")
def test_global_rate_limiting_returns_429(client: TestClient):
    # Hit /health more than 10 times quickly from same client IP
    statuses = []
    for _ in range(12):
        r = client.get("/health")
        statuses.append(r.status_code)

    # At least one request should be rate limited
    assert 429 in statuses
