"""Tests for recipe CRUD endpoints."""
import json
from unittest.mock import MagicMock, patch

from tests.conftest import MOCK_TRANSLATED, CAPTCHA_DUMMY, password_hash
from app import models
from tests.conftest import TestSessionLocal


def _create_recipe(client, auth_headers, raw_input="מרק עגבניות"):
    with patch("app.routers.recipes.translate_recipe", return_value=MOCK_TRANSLATED):
        r = client.post(
            "/api/recipes/",
            json={"raw_input": raw_input},
            headers=auth_headers,
        )
    assert r.status_code == 201
    return r.json()


def test_create_recipe_returns_structured_json(client, auth_headers):
    data = _create_recipe(client, auth_headers)
    assert data["title_pl"] == "Zupa Pomidorowa"
    assert data["title_original"] == "מרק עגבניות"
    assert len(data["ingredients_pl"]) == 3
    assert len(data["steps_pl"]) == 3
    assert "id" in data
    assert data["user_id"] is not None


def test_create_recipe_saved_to_db(client, auth_headers):
    created = _create_recipe(client, auth_headers)
    r = client.get(f"/api/recipes/{created['id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_list_recipes_returns_only_current_users(client, auth_headers):
    # Create recipe for user A
    _create_recipe(client, auth_headers)

    # Register and login as user B (patch starter recipes so B gets none on login — we are testing isolation)
    with patch("app.routers.auth.send_verification_email"), patch(
        "app.routers.auth._verify_turnstile", return_value=True
    ), patch("app.routers.auth.ensure_starter_recipes_for_user"):
        client.post(
            "/api/auth/register",
            json={
                "email": "b@example.com",
                "password_hash": password_hash("bpass1234"),
                "captcha_token": CAPTCHA_DUMMY,
                "ui_language": "en",
                "target_language": "pl",
                "target_country": "PL",
                "target_city": "Wrocław",
            },
        )
        r = client.post("/api/auth/login", json={"email": "b@example.com", "password_hash": password_hash("bpass1234")})
    b_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # User B should see zero recipes (starter recipes were patched out)
    r = client.get("/api/recipes/", headers=b_headers)
    assert r.status_code == 200
    assert r.json() == []

    # User A should see their recipe
    r = client.get("/api/recipes/", headers=auth_headers)
    assert len(r.json()) == 1


def test_starter_recipes_added_on_first_login(client):
    """New user gets 3 starter recipes on first login (fallback when no OpenAI key)."""
    with patch("app.routers.auth.send_verification_email"), patch(
        "app.routers.auth._verify_turnstile", return_value=True
    ):
        client.post(
            "/api/auth/register",
            json={
                "email": "starter@example.com",
                "password_hash": password_hash("pass1234"),
                "captcha_token": CAPTCHA_DUMMY,
                "ui_language": "en",
                "target_language": "pl",
                "target_country": "PL",
                "target_city": "Wrocław",
            },
        )
    r = client.post("/api/auth/login", json={"email": "starter@example.com", "password_hash": password_hash("pass1234")})
    assert r.status_code == 200
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.get("/api/recipes/", headers=headers)
    assert r.status_code == 200
    recipes = r.json()
    assert len(recipes) == 3
    for rec in recipes:
        assert "title_pl" in rec
        assert "ingredients_pl" in rec
        assert "steps_pl" in rec
        assert rec.get("author_name") or rec.get("author_bio")


def test_get_recipe_not_found(client, auth_headers):
    r = client.get("/api/recipes/99999", headers=auth_headers)
    assert r.status_code == 404


def test_get_recipe_other_user_returns_404(client, auth_headers):
    created = _create_recipe(client, auth_headers)

    with patch("app.routers.auth.send_verification_email"), patch(
        "app.routers.auth._verify_turnstile", return_value=True
    ):
        client.post(
            "/api/auth/register",
            json={
                "email": "other@example.com",
                "password_hash": password_hash("opass1234"),
                "captcha_token": CAPTCHA_DUMMY,
                "ui_language": "en",
                "target_language": "pl",
                "target_country": "PL",
                "target_city": "Wrocław",
            },
        )
    r = client.post("/api/auth/login", json={"email": "other@example.com", "password_hash": password_hash("opass1234")})
    other_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.get(f"/api/recipes/{created['id']}", headers=other_headers)
    assert r.status_code == 404


def test_delete_recipe(client, auth_headers):
    created = _create_recipe(client, auth_headers)
    r = client.delete(f"/api/recipes/{created['id']}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/api/recipes/{created['id']}", headers=auth_headers)
    assert r.status_code == 404


def test_delete_recipe_removes_from_shopping_list(client, auth_headers):
    created = _create_recipe(client, auth_headers)
    recipe_id = created["id"]

    # Add to shopping list
    r = client.post("/api/shopping-list/add", json={"recipe_id": recipe_id}, headers=auth_headers)
    assert recipe_id in r.json()["recipe_ids"]

    # Delete recipe
    client.delete(f"/api/recipes/{recipe_id}", headers=auth_headers)

    # Shopping list should be empty
    r = client.get("/api/shopping-list/recipes", headers=auth_headers)
    assert recipe_id not in r.json()["recipe_ids"]


def test_favorite_recipe(client, auth_headers):
    created = _create_recipe(client, auth_headers)
    assert created["is_favorite"] is False

    r = client.patch(
        f"/api/recipes/{created['id']}/favorite",
        json={"is_favorite": True},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["is_favorite"] is True

    # Toggle back
    r = client.patch(
        f"/api/recipes/{created['id']}/favorite",
        json={"is_favorite": False},
        headers=auth_headers,
    )
    assert r.json()["is_favorite"] is False


def test_add_notes_to_recipe(client, auth_headers):
    created = _create_recipe(client, auth_headers)
    assert created["user_notes"] is None

    r = client.patch(
        f"/api/recipes/{created['id']}/notes",
        json={"user_notes": "Dodaj trochę pieprzu."},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["user_notes"] == "Dodaj trochę pieprzu."


def test_add_notes_can_be_cleared(client, auth_headers):
    created = _create_recipe(client, auth_headers)
    client.patch(
        f"/api/recipes/{created['id']}/notes",
        json={"user_notes": "Some note"},
        headers=auth_headers,
    )
    r = client.patch(
        f"/api/recipes/{created['id']}/notes",
        json={"user_notes": None},
        headers=auth_headers,
    )
    assert r.json()["user_notes"] is None


def test_create_recipe_without_openai_key_returns_503(client, auth_headers):
    """POST /api/recipes/ must return 503 when OPENAI_API_KEY is not configured.
    Regression: missing key produced an unhandled 500; now returns a clear 503."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
        r = client.post(
            "/api/recipes/",
            json={"raw_input": "מרק עגבניות"},
            headers=auth_headers,
        )
    assert r.status_code == 503
    assert "OPENAI_API_KEY" in r.json()["detail"]


def test_recipe_input_sanitization_strips_html_and_limits_length(client, auth_headers):
    raw = "<script>alert('x')</script> " + "a" * 20000
    with patch("app.routers.recipes.translate_recipe", return_value=MOCK_TRANSLATED):
        r = client.post(
            "/api/recipes/",
            json={"raw_input": raw},
            headers=auth_headers,
        )
    assert r.status_code == 201
    data = r.json()
    # Ensure raw_input stored on recipe is at most 10000 chars and has no HTML tags
    assert len(data["raw_input"]) <= 10000
    assert "<script>" not in data["raw_input"]


def test_create_recipe_requires_raw_input_or_source_url(client, auth_headers):
    r = client.post("/api/recipes/", json={}, headers=auth_headers)
    assert r.status_code == 422

    r = client.post(
        "/api/recipes/",
        json={"raw_input": "text", "source_url": "https://example.com/recipe"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_create_recipe_from_url_rejects_invalid_url(client, auth_headers):
    r = client.post(
        "/api/recipes/",
        json={"source_url": "file:///etc/passwd"},
        headers=auth_headers,
    )
    assert r.status_code == 400

    r = client.post(
        "/api/recipes/",
        json={"source_url": "http://localhost/recipe"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_create_recipe_from_url_fetches_and_translates(client, auth_headers):
    html = """
    <html><head><script>nope</script></head>
    <body><p>מרק עגבניות</p><p>Składniki: pomidory</p></body></html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_resp.content = html.encode("utf-8")

    def split_mock(page_text):
        # Return one chunk (full page) so translate_recipe is called once
        return [(page_text or "").strip()] if (page_text or "").strip() else []

    with patch("app.routers.recipes.httpx.get", return_value=mock_resp), patch(
        "app.routers.recipes.split_page_into_recipes", side_effect=split_mock
    ), patch("app.routers.recipes.translate_recipe", return_value=MOCK_TRANSLATED):
        r = client.post(
            "/api/recipes/",
            json={"source_url": "https://example.com/recipe"},
            headers=auth_headers,
        )
    assert r.status_code == 201
    data = r.json()
    assert data["title_pl"] == "Zupa Pomidorowa"
    # Fetched text should be sanitized (no script tags)
    assert "nope" not in data["raw_input"]
    assert "מרק" in data["raw_input"] or "pomidory" in data["raw_input"]


def test_create_recipe_from_url_two_recipes_returns_two(client, auth_headers):
    """When page has two recipes, extraction yields 2 chunks and API returns 2 created recipes."""
    html = "<html><body><p>Recipe 1 and Recipe 2 page</p></body></html>"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_resp.content = html.encode("utf-8")

    def split_mock(page_text):
        # Simulate extractor finding two recipes: return two chunks
        return [
            "First Recipe\n\nIngredients:\n- flour\n\nSteps:\n1. Mix.",
            "Second Recipe\n\nIngredients:\n- sugar\n\nSteps:\n1. Bake.",
        ] if (page_text or "").strip() else []

    first_translated = {**MOCK_TRANSLATED, "title_pl": "First", "title_original": "First Recipe"}
    second_translated = {**MOCK_TRANSLATED, "title_pl": "Second", "title_original": "Second Recipe"}

    with patch("app.routers.recipes.httpx.get", return_value=mock_resp), patch(
        "app.routers.recipes.split_page_into_recipes", side_effect=split_mock
    ), patch(
        "app.routers.recipes.translate_recipe",
        side_effect=[first_translated, second_translated],
    ):
        r = client.post(
            "/api/recipes/",
            json={"source_url": "https://example.com/two-recipes"},
            headers=auth_headers,
        )
    assert r.status_code == 201
    data = r.json()
    assert "recipes" in data
    recipes = data["recipes"]
    assert len(recipes) == 2
    assert recipes[0]["title_pl"] == "First"
    assert recipes[1]["title_pl"] == "Second"


def test_extract_recipes_from_page_returns_two_when_model_returns_two():
    """Extractor returns 2 recipes when OpenAI response contains 2."""
    from app.services.translation import extract_recipes_from_page

    two_recipes = {
        "recipes": [
            {"title": "Recipe A", "ingredients": ["a1", "a2"], "instructions": ["step 1"]},
            {"title": "Recipe B", "ingredients": ["b1"], "instructions": ["step 1", "step 2"]},
        ]
    }
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(two_recipes)))]

    with patch("app.services.translation.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response
        result = extract_recipes_from_page("Page with two recipes")
    assert len(result) == 2
    assert result[0]["title"] == "Recipe A"
    assert result[0]["ingredients"] == ["a1", "a2"]
    assert result[0]["instructions"] == ["step 1"]
    assert result[1]["title"] == "Recipe B"
    assert result[1]["ingredients"] == ["b1"]
    assert result[1]["instructions"] == ["step 1", "step 2"]


# Page text that mimics mako.co.il style: two distinct recipes (pancakes + fruit salad).
# Each has its own title, מרכיבים (ingredients), and הוראות (instructions).
TWO_RECIPE_MAKO_STYLE_PAGE = """
פנקייק יוגורט
מרכיבים:
2 ביצים
200 מ"ל חלב
150 גרם קמח
1 כפית אבקת אפייה
ספריי שמן לטיגון
הוראות:
מערבבים את הביצים והחלב. מוסיפים קמח ואבקת אפייה. מטגנים במחבת עם שמן.

סלט פירות
מרכיבים:
חצי מלון קלוף וחתוך לקוביות
חצי אננס קלוף וחתוך לקוביות
אשכול ענבים חצויים
חופן עלי נענע קצוצים
הוראות:
מערבבים בקערה את כל הפירות. מוסיפים נענע ומשהים כחצי שעה.
"""


def test_extract_recipes_splits_mako_style_two_recipes_with_heuristic():
    """When model returns 1 merged recipe but page has two מרכיבים blocks, heuristic splits and re-extracts → 2 recipes."""
    from app.services.translation import extract_recipes_from_page

    # First call (full page): model returns 1 merged recipe. Second/third (chunks): each returns 1 recipe.
    merged = {
        "recipes": [
            {
                "title": "פנקייק יוגורט",
                "ingredients": ["ביצים", "חלב", "קמח", "מלון", "אננס"],
                "instructions": ["מערבבים", "מטגנים", "מערבבים פירות"],
            }
        ]
    }
    pancake = {
        "recipes": [
            {"title": "פנקייק יוגורט", "ingredients": ["ביצים", "חלב", "קמח"], "instructions": ["מערבבים", "מטגנים"]}
        ]
    }
    fruit_salad = {
        "recipes": [
            {"title": "סלט פירות", "ingredients": ["מלון", "אננס", "ענבים"], "instructions": ["מערבבים בקערה"]}
        ]
    }
    call_responses = [merged, pancake, fruit_salad]
    call_count = [0]

    def create_mock(content):
        mock = MagicMock()
        mock.choices = [MagicMock(message=MagicMock(content=content))]
        return mock

    def fake_create(*args, **kwargs):
        idx = min(call_count[0], len(call_responses) - 1)
        call_count[0] += 1
        return create_mock(json.dumps(call_responses[idx]))

    with patch("app.services.translation.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = fake_create
        mock_openai.return_value = mock_client
        result = extract_recipes_from_page(TWO_RECIPE_MAKO_STYLE_PAGE)
    assert len(result) >= 2, (
        f"Heuristic should split page with two מרכיבים blocks and return 2 recipes, got {len(result)}"
    )
    titles = [r["title"] for r in result]
    assert len(titles) == len(set(titles)), "Recipe titles must be distinct"


def test_extract_recipes_splits_mako_style_two_recipes_integration():
    """Integration: real API on mako-style page should yield 2 recipes (skipped if no valid OPENAI_API_KEY)."""
    import os
    import pytest
    from app.services.translation import extract_recipes_from_page

    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key or key.startswith("test-"):
        pytest.skip("OPENAI_API_KEY not set or placeholder (set real key to run integration)")
    result = extract_recipes_from_page(TWO_RECIPE_MAKO_STYLE_PAGE)
    assert len(result) >= 2, (
        f"Expected at least 2 recipes from mako-style page (pancakes + fruit salad), got {len(result)}. "
        "Extractor should not merge two distinct recipes into one."
    )
    titles = [r["title"] for r in result]
    assert len(titles) == len(set(titles)), "Recipe titles must be distinct"


def test_create_recipe_calls_translate_with_user_target_settings(client, auth_headers):
    """Translation is called with user's target_language, target_country, target_city."""
    with patch("app.routers.recipes.translate_recipe", return_value=MOCK_TRANSLATED) as mock_translate:
        r = client.post(
            "/api/recipes/",
            json={"raw_input": "Hebrew recipe text"},
            headers=auth_headers,
        )
    assert r.status_code == 201
    mock_translate.assert_called_once()
    call_kwargs = mock_translate.call_args[1]
    assert call_kwargs["target_language"] == "pl"
    assert call_kwargs["target_country"] == "PL"
    assert call_kwargs["target_city"] == "Wrocław"
    assert call_kwargs["raw_input"] == "Hebrew recipe text"


def test_create_recipe_saves_detected_language(client, auth_headers):
    """Recipe is saved with detected_language from translation result."""
    with patch("app.routers.recipes.translate_recipe", return_value=MOCK_TRANSLATED):
        r = client.post(
            "/api/recipes/",
            json={"raw_input": "text"},
            headers=auth_headers,
        )
    assert r.status_code == 201
    assert r.json().get("detected_language") == "he"


def test_create_recipe_not_a_recipe_returns_422_and_does_not_consume_quota(client, auth_headers, registered_user):
    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == registered_user["email"]).first()
        user.transformations_used = 0
        user.transformations_limit = 5
        db.commit()
    finally:
        db.close()

    with patch("app.routers.recipes.translate_recipe", side_effect=ValueError("NOT_A_RECIPE: classifier=false")):
        r = client.post(
            "/api/recipes/",
            json={"raw_input": "hello this is not a recipe"},
            headers=auth_headers,
        )
    assert r.status_code == 422
    assert "doesn't look like a recipe" in r.json()["detail"].lower()

    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == registered_user["email"]).first()
        assert user.transformations_used == 0
    finally:
        db.close()


def test_relocalize_updates_recipe_and_consumes_quota(client, auth_headers, registered_user, recipe):
    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == registered_user["email"]).first()
        user.transformations_used = 0
        user.transformations_limit = 5
        # Change user locale so recipe (created with pl/PL) needs relocalization
        user.target_language = "en"
        user.target_country = "US"
        user.target_city = "New York"
        db.commit()
    finally:
        db.close()

    relocalized = dict(MOCK_TRANSLATED)
    relocalized["title_pl"] = "Zupa Pomidorowa (PL 2)"
    relocalized["ingredients_pl"] = ["1 pomidor"]
    with patch("app.routers.recipes.translate_recipe", return_value=relocalized):
        r = client.post(f"/api/recipes/{recipe['id']}/relocalize", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["title_pl"] == "Zupa Pomidorowa (PL 2)"
    assert data["ingredients_pl"] == ["1 pomidor"]

    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == registered_user["email"]).first()
        assert user.transformations_used == 1
    finally:
        db.close()
