"""Tests for anonymous trial: /api/trial/start and trial quota enforcement."""
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app import models
from app.auth import create_trial_token, decode_trial_token
from tests.conftest import TestSessionLocal


def _three_starter_recipes():
    return [
        {"title": "Recipe 1", "ingredients": ["a", "b"], "steps": ["1", "2"], "author_name": "Chef A", "author_bio": "Famous", "author_image_url": None},
        {"title": "Recipe 2", "ingredients": ["c"], "steps": ["1"], "author_name": "Chef B", "author_bio": "TV host", "author_image_url": None},
        {"title": "Recipe 3", "ingredients": ["d", "e"], "steps": ["1", "2", "3"], "author_name": None, "author_bio": None, "author_image_url": None},
    ]


@patch("app.routers.trial._geo_from_ip")
@patch("app.routers.trial.get_starter_recipes")
def test_trial_start_returns_token_and_recipes(mock_starter, mock_geo, client):
    mock_geo.return_value = {"country_code": "PL"}
    mock_starter.return_value = _three_starter_recipes()

    r = client.post("/api/trial/start", json={})
    assert r.status_code == 200
    data = r.json()
    assert "trial_token" in data
    assert data["country"] == "PL"
    assert data["language"] == "pl"
    assert len(data["recipes"]) == 3
    assert data["remaining_actions"] == 5
    assert data["recipes"][0]["title"] == "Recipe 1"
    assert data["recipes"][0]["author_name"] == "Chef A"


@patch("app.routers.trial._geo_from_ip")
@patch("app.routers.trial.get_starter_recipes")
def test_trial_start_ip_guard_429(mock_starter, mock_geo, client):
    mock_geo.return_value = {"country_code": "US"}
    mock_starter.return_value = _three_starter_recipes()

    # Create 3 trial sessions from same IP in last 24h
    db = TestSessionLocal()
    try:
        now = datetime.now(timezone.utc)
        for i in range(3):
            s = models.TrialSession(
                token_id=f"tid-{i}-xxxxxxxxxxxxxxxx",
                country="US",
                language="en",
                used_actions=0,
                ip_address="192.168.1.100",
                created_at=now,
                last_seen_at=now,
            )
            db.add(s)
        db.commit()
    finally:
        db.close()

    # Request with same IP (via x-forwarded-for)
    with patch("app.routers.trial._client_ip", return_value="192.168.1.100"):
        r = client.post("/api/trial/start", json={})
    assert r.status_code == 429
    assert "trial" in (r.json().get("detail") or "").lower()


def test_decode_trial_token_valid():
    token_id = "test-token-id-123"
    token = create_trial_token(token_id)
    payload = decode_trial_token(token)
    assert payload is not None
    assert payload.get("sub") == token_id
    assert payload.get("type") == "trial"


def test_decode_trial_token_invalid_returns_none():
    assert decode_trial_token("invalid") is None
    assert decode_trial_token("") is None
    # User JWT should not be accepted as trial
    from app.auth import create_access_token
    user_token = create_access_token(1)
    assert decode_trial_token(user_token) is None


@patch("app.routers.recipes.suggest_recipe_from_ingredients")
def test_trial_quota_5_actions_then_402(mock_suggest, client):
    mock_suggest.return_value = {"title": "Test", "ingredients": [], "steps": [], "missing_ingredients": []}

    # Create trial session and token
    db = TestSessionLocal()
    try:
        token_id = "quota-test-token-id"
        session = models.TrialSession(
            token_id=token_id,
            country="PL",
            language="pl",
            used_actions=0,
            ip_address=None,
            created_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()
    finally:
        db.close()

    trial_token = create_trial_token(token_id)
    headers = {"Authorization": f"Bearer {trial_token}"}

    # 5 requests should succeed
    for _ in range(5):
        r = client.post(
            "/api/recipes/what-can-i-make",
            json={"ingredients": ["eggs"], "source": "ai", "assume_pantry": True},
            headers=headers,
        )
        assert r.status_code == 200, r.json()

    # 6th should be 402 trial exhausted
    r = client.post(
        "/api/recipes/what-can-i-make",
        json={"ingredients": ["eggs"], "source": "ai", "assume_pantry": True},
        headers=headers,
    )
    assert r.status_code == 402
    data = r.json()
    assert data.get("detail", {}).get("code") == "trial_exhausted" or "trial" in str(data.get("detail", "")).lower()


def test_trial_quota_missing_token_401(client):
    r = client.post(
        "/api/recipes/what-can-i-make",
        json={"ingredients": ["eggs"], "source": "ai", "assume_pantry": True},
    )
    assert r.status_code == 401


def test_trial_quota_invalid_token_401(client):
    r = client.post(
        "/api/recipes/what-can-i-make",
        json={"ingredients": ["eggs"], "source": "ai", "assume_pantry": True},
        headers={"Authorization": "Bearer invalid-trial-token"},
    )
    assert r.status_code == 401
