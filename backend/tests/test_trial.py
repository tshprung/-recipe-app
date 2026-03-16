"""Tests for anonymous trial: /api/trial/start and trial quota enforcement."""
import re
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app import models
from app.auth import create_trial_token, decode_trial_token
from app.services.starter_recipes import _fallback_recipes
from tests.conftest import TestSessionLocal


def _three_starter_recipes():
    """Starter recipes must include amounts in ingredients (e.g. 500g flour)."""
    return [
        {"title": "Recipe 1", "ingredients": ["500g flour", "2 cups water", "1 tsp salt"], "steps": ["Mix.", "Bake."], "author_name": "Chef A", "author_bio": "Famous", "author_image_url": None, "tags": ["soup"]},
        {"title": "Recipe 2", "ingredients": ["300g chicken", "1 tbsp oil"], "steps": ["Fry."], "author_name": "Chef B", "author_bio": "TV host", "author_image_url": None, "tags": ["main"]},
        {"title": "Recipe 3", "ingredients": ["200g sugar", "3 eggs", "100g butter"], "steps": ["Mix.", "Bake.", "Cool."], "author_name": None, "author_bio": None, "author_image_url": None, "tags": ["dessert"]},
    ]


@patch("app.routers.trial._geo_from_ip")
def test_trial_start_returns_token_no_initial_recipes(mock_geo, client):
    mock_geo.return_value = {"country_code": "PL"}

    r = client.post("/api/trial/start", json={})
    assert r.status_code == 200
    data = r.json()
    assert "trial_token" in data
    assert data["country"] == "PL"
    assert data["language"] == "pl"
    assert data["recipes"] == []
    assert data["remaining_actions"] == 5


@patch("app.routers.trial._geo_from_ip")
def test_trial_start_creates_session_no_recipes(mock_geo, client):
    """New trial creates a session but no initial recipes."""
    mock_geo.return_value = {"country_code": "PL"}

    r = client.post("/api/trial/start", json={})
    assert r.status_code == 200
    token = r.json()["trial_token"]
    payload = decode_trial_token(token)
    assert payload is not None
    token_id = payload.get("sub")

    db = TestSessionLocal()
    try:
        session = db.query(models.TrialSession).filter(models.TrialSession.token_id == token_id).first()
        assert session is not None
        recipes = db.query(models.Recipe).filter(models.Recipe.trial_session_id == session.id).all()
        assert len(recipes) == 0
    finally:
        db.close()


@patch("app.routers.trial._geo_from_ip")
def test_trial_start_accepts_country_and_language(mock_geo, client):
    """Trial start accepts optional country and language in body."""
    mock_geo.return_value = {"country_code": "XX"}

    r = client.post("/api/trial/start", json={"country": "DE", "language": "de"})
    assert r.status_code == 200
    data = r.json()
    assert data["country"] == "DE"
    assert data["language"] == "de"
    assert data["recipes"] == []


def test_fallback_starter_recipes_ingredients_have_amounts():
    """Fallback starter recipes (PL and EN) must include amounts in ingredients."""
    amount_pattern = re.compile(r"\d")
    for lang in ("pl", "en"):
        recipes = _fallback_recipes(lang)
        assert len(recipes) == 3
        for r in recipes:
            ingredients = r.get("ingredients") or []
            assert ingredients, f"Fallback recipe {r.get('title')} has no ingredients"
            combined = " ".join(str(i) for i in ingredients)
            assert amount_pattern.search(combined), f"Fallback ingredients should include amounts: {ingredients}"


@patch("app.routers.trial._geo_from_ip")
def test_trial_start_resume_by_device_id_returns_same_credits(mock_geo, client):
    """Sending device_id of an existing trial resumes it and returns actual remaining_actions, not 5."""
    mock_geo.return_value = {"country_code": "PL"}

    r = client.post("/api/trial/start", json={})
    assert r.status_code == 200
    data = r.json()
    device_id = data.get("device_id")
    assert device_id, "First trial start must return device_id"
    assert data["remaining_actions"] == 5
    assert data["recipes"] == []

    # Use 2 actions (e.g. quota enforcement would increment used_actions)
    db = TestSessionLocal()
    try:
        payload = decode_trial_token(data["trial_token"])
        session = db.query(models.TrialSession).filter(
            models.TrialSession.token_id == payload["sub"],
        ).first()
        assert session is not None
        session.used_actions = 2
        db.commit()
    finally:
        db.close()

    # Resume with device_id: should get remaining_actions=3, not 5
    r2 = client.post("/api/trial/start", json={"device_id": device_id})
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["remaining_actions"] == 3
    assert data2["device_id"] == device_id
    assert len(data2["recipes"]) == 0


@patch("app.routers.trial._geo_from_ip")
def test_trial_start_ip_guard_429(mock_geo, client):
    mock_geo.return_value = {"country_code": "US"}

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
