"""Tests for recipe CRUD endpoints."""
from unittest.mock import patch

from tests.conftest import MOCK_TRANSLATED


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

    # Register and login as user B
    client.post("/api/auth/register", json={"email": "b@example.com", "password": "bpass"})
    r = client.post("/api/auth/login", json={"email": "b@example.com", "password": "bpass"})
    b_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # User B should see zero recipes
    r = client.get("/api/recipes/", headers=b_headers)
    assert r.status_code == 200
    assert r.json() == []

    # User A should see their recipe
    r = client.get("/api/recipes/", headers=auth_headers)
    assert len(r.json()) == 1


def test_get_recipe_not_found(client, auth_headers):
    r = client.get("/api/recipes/99999", headers=auth_headers)
    assert r.status_code == 404


def test_get_recipe_other_user_returns_404(client, auth_headers):
    created = _create_recipe(client, auth_headers)

    client.post("/api/auth/register", json={"email": "other@example.com", "password": "opass"})
    r = client.post("/api/auth/login", json={"email": "other@example.com", "password": "opass"})
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
