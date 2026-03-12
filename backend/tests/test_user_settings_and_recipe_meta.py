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

