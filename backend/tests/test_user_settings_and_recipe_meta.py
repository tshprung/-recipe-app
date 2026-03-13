from unittest.mock import patch

from tests.conftest import CAPTCHA_DUMMY


def test_patch_user_settings_default_servings_and_allergens(client, auth_headers):
    payload = {
        "ui_language": "en",
        "target_language": "pl",
        "target_country": "PL",
        "target_city": "Wrocław",
        "target_zip": "50-001",
        "default_servings": 5,
        "allergens": ["gluten_cereals", "milk", "eggs"],
        "custom_allergens_text": "kiwi, strawberries",
    }
    r = client.patch("/api/users/me/settings", json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["default_servings"] == 5
    assert set(data["allergens"]) == {"gluten_cereals", "milk", "eggs"}
    assert data["custom_allergens_text"] == "kiwi, strawberries"


def test_patch_user_settings_rejects_unknown_allergen(client, auth_headers):
    payload = {
        "ui_language": "en",
        "target_language": "pl",
        "target_country": "PL",
        "target_city": "Wrocław",
        "target_zip": "50-001",
        "default_servings": 4,
        "allergens": ["milk", "unknown_allergen"],
    }
    r = client.patch("/api/users/me/settings", json=payload, headers=auth_headers)
    assert r.status_code == 422


def test_patch_recipe_meta_rating_and_times(client, auth_headers):
    from tests.test_recipes import _create_recipe

    created = _create_recipe(client, auth_headers)
    recipe_id = created["id"]

    r = client.patch(f"/api/recipes/{recipe_id}/meta", json={"rating": 4}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["user_rating"] == 4

    r = client.patch(
        f"/api/recipes/{recipe_id}/meta",
        json={"prep_time_minutes": 10, "cook_time_minutes": 25},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["prep_time_minutes"] == 10
    assert data["cook_time_minutes"] == 25

    # Clear rating
    r = client.patch(f"/api/recipes/{recipe_id}/meta", json={"rating": None}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["user_rating"] is None


def _three_starter_recipes():
    """Starter recipes must include amounts in ingredients."""
    return [
        {"title": "Recipe 1", "ingredients": ["500g flour", "2 cups water", "1 tsp salt"], "steps": ["Mix.", "Bake."], "author_name": "Chef A", "author_bio": "Famous", "tags": ["soup"]},
        {"title": "Recipe 2", "ingredients": ["300g chicken", "1 tbsp oil"], "steps": ["Fry."], "author_name": "Chef B", "author_bio": "TV host", "tags": ["main"]},
        {"title": "Recipe 3", "ingredients": ["200g sugar", "3 eggs", "100g butter"], "steps": ["Mix.", "Bake.", "Cool."], "author_name": None, "author_bio": None, "tags": ["dessert"]},
    ]


@patch("app.services.starter_recipes.get_starter_recipes")
def test_fetch_starter_recipes_creates_recipes_with_no_image(mock_get_starter, client, auth_headers):
    """Fetch starter recipes (Settings) creates recipes with image_url=None."""
    mock_get_starter.return_value = _three_starter_recipes()
    r = client.post("/api/users/me/fetch-starter-recipes", headers=auth_headers)
    assert r.status_code == 204
    r = client.get("/api/recipes/", headers=auth_headers)
    assert r.status_code == 200
    recipes = r.json()
    assert len(recipes) >= 3
    for rec in recipes[:3]:
        assert rec.get("image_url") is None

