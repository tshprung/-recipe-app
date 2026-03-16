from unittest.mock import patch

from app import models
from .conftest import TestSessionLocal, password_hash, CAPTCHA_DUMMY


@patch("app.routers.recipes.suggest_recipes_from_preferences")
def test_discover_persists_preferences_and_returns_single_recipe(mock_suggest, client):
    """Discover endpoint should save preferences on the user and return exactly one suggestion."""
    # Register and verify a user
    from app.main import app  # noqa: F401  # ensure models are imported
    with patch("app.routers.auth.send_verification_email"), patch(
        "app.routers.auth._verify_turnstile", return_value=True
    ):
        r = client.post(
            "/api/auth/register",
            json={
                "email": "discover@example.com",
                "password_hash": password_hash("pass1234"),
                "captcha_token": CAPTCHA_DUMMY,
                "ui_language": "en",
                "target_language": "en",
                "target_country": "US",
                "target_city": "New York",
            },
        )
    assert r.status_code == 201
    user_data = r.json()

    # Mark verified with generous quota
    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter_by(id=user_data["id"]).first()
        user.is_verified = True
        user.transformations_limit = 100
        user.transformations_used = 0
        db.commit()
    finally:
        db.close()

    # Login to get auth headers
    with patch("app.routers.auth.ensure_starter_recipes_for_user"):
        r = client.post(
            "/api/auth/login",
            json={"email": "discover@example.com", "password_hash": password_hash("pass1234")},
        )
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mock AI suggestions: two recipes, but endpoint should only return the first/best match.
    mock_suggest.return_value = [
        {"title": "Pasta Primavera", "ingredients": ["pasta"], "steps": ["cook pasta"]},
        {"title": "Tomato Soup", "ingredients": ["tomatoes"], "steps": ["cook soup"]},
    ]

    payload = {
        "dish_types": ["pasta", "soups"],
        "diet_filters": ["vegetarian"],
        "max_time_minutes": 30,
        "allergens": ["milk"],
        "custom_avoid_text": "kiwi",
    }
    r = client.post("/api/recipes/discover", json=payload, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) == 1
    assert data["suggestions"][0]["title"] == "Pasta Primavera"

    # Preferences should be saved on the user for next time.
    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter_by(id=user_data["id"]).first()
        assert user.dish_preferences == ["pasta", "soups"]
        assert user.diet_filters == ["vegetarian"]
        assert user.allergens == ["milk"]
        assert "kiwi" in (user.custom_allergens_text or "")
    finally:
        db.close()

