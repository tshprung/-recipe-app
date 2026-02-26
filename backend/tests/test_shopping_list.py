"""Tests for the shopping list endpoints."""
from unittest.mock import patch

from tests.conftest import MOCK_TRANSLATED

MOCK_CATEGORIES = {
    "Warzywa i owoce": ["500g pomidory", "1 sztuka cebula"],
    "Nabiał": [],
    "Mięso i ryby": [],
    "Przyprawy i sosy": ["2 ząbki czosnek"],
    "Inne": [],
}


def _create_recipe(client, auth_headers):
    with patch("app.routers.recipes.translate_recipe", return_value=MOCK_TRANSLATED):
        r = client.post("/api/recipes/", json={"raw_input": "test"}, headers=auth_headers)
    assert r.status_code == 201
    return r.json()


def test_add_recipe_to_shopping_list(client, auth_headers, recipe):
    r = client.post(
        "/api/shopping-list/add",
        json={"recipe_id": recipe["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert recipe["id"] in r.json()["recipe_ids"]


def test_add_recipe_twice_only_appears_once(client, auth_headers, recipe):
    client.post("/api/shopping-list/add", json={"recipe_id": recipe["id"]}, headers=auth_headers)
    r = client.post("/api/shopping-list/add", json={"recipe_id": recipe["id"]}, headers=auth_headers)
    assert r.json()["recipe_ids"].count(recipe["id"]) == 1


def test_get_recipe_ids_empty(client, auth_headers):
    r = client.get("/api/shopping-list/recipes", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["recipe_ids"] == []


def test_get_recipe_ids_after_add(client, auth_headers, recipe):
    client.post("/api/shopping-list/add", json={"recipe_id": recipe["id"]}, headers=auth_headers)
    r = client.get("/api/shopping-list/recipes", headers=auth_headers)
    assert recipe["id"] in r.json()["recipe_ids"]


def test_get_shopping_list_merged_ingredients(client, auth_headers, recipe):
    client.post("/api/shopping-list/add", json={"recipe_id": recipe["id"]}, headers=auth_headers)
    with patch("app.routers.shopping_lists.categorize_ingredients", return_value=MOCK_CATEGORIES):
        r = client.get("/api/shopping-list/", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "Warzywa i owoce" in data["items"]
    assert recipe["id"] in data["recipe_ids"]


def test_remove_recipe_from_shopping_list(client, auth_headers, recipe):
    client.post("/api/shopping-list/add", json={"recipe_id": recipe["id"]}, headers=auth_headers)
    r = client.delete(f"/api/shopping-list/remove/{recipe['id']}", headers=auth_headers)
    assert r.status_code == 200
    assert recipe["id"] not in r.json()["recipe_ids"]


def test_shopping_list_is_per_user(client, auth_headers, recipe):
    # User A adds a recipe
    client.post("/api/shopping-list/add", json={"recipe_id": recipe["id"]}, headers=auth_headers)

    # User B registers and checks their list
    client.post("/api/auth/register", json={"email": "b@example.com", "password": "bpass"})
    r = client.post("/api/auth/login", json={"email": "b@example.com", "password": "bpass"})
    b_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.get("/api/shopping-list/recipes", headers=b_headers)
    assert r.json()["recipe_ids"] == []


def test_add_nonexistent_recipe_returns_404(client, auth_headers):
    r = client.post("/api/shopping-list/add", json={"recipe_id": 99999}, headers=auth_headers)
    assert r.status_code == 404
