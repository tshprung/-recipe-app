"""Tests for ingredient substitution reporting and application."""
from unittest.mock import patch

from tests.conftest import MOCK_TRANSLATED


def test_save_substitution(client, auth_headers):
    r = client.post(
        "/api/substitutions/report",
        json={
            "original_label": "tahini",
            "better_substitution": "pasta sezamowa",
            "source_country": "IL",
            "target_country": "PL",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["ok"] is True


def test_save_substitution_requires_auth(client):
    r = client.post(
        "/api/substitutions/report",
        json={
            "original_label": "tahini",
            "better_substitution": "pasta sezamowa",
        },
    )
    assert r.status_code == 401


def test_substitution_applied_in_shopping_list(client, auth_headers, recipe):
    """
    Save a substitution whose name matches an ingredient in the recipe,
    then verify the shopping list uses the substituted label.
    """
    # The recipe has ingredient "2 ząbki czosnek" — we save a substitution for it
    client.post(
        "/api/substitutions/report",
        json={
            "original_label": "2 ząbki czosnek",
            "better_substitution": "1 łyżeczka czosnku granulowanego",
            "source_country": "IL",
            "target_country": "PL",
        },
        headers=auth_headers,
    )

    # Add recipe to shopping list
    client.post("/api/shopping-list/add", json={"recipe_id": recipe["id"]}, headers=auth_headers)

    # Capture the ingredients passed to categorize_ingredients
    captured = {}

    def fake_categorize(ingredients):
        captured["ingredients"] = ingredients
        return {
            "Warzywa i owoce": ingredients,
            "Nabiał": [],
            "Mięso i ryby": [],
            "Przyprawy i sosy": [],
            "Inne": [],
        }

    with patch("app.routers.shopping_lists.categorize_ingredients", side_effect=fake_categorize):
        r = client.get("/api/shopping-list/", headers=auth_headers)

    assert r.status_code == 200
    ingredients = captured["ingredients"]
    # The substituted label should appear; the original should not
    assert "1 łyżeczka czosnku granulowanego" in ingredients
    assert "2 ząbki czosnek" not in ingredients


def test_substitution_not_applied_for_wrong_country(client, auth_headers, recipe):
    """Substitution with different source_country must NOT be applied."""
    client.post(
        "/api/substitutions/report",
        json={
            "original_label": "2 ząbki czosnek",
            "better_substitution": "garlic powder",
            "source_country": "US",   # different country
            "target_country": "PL",
        },
        headers=auth_headers,
    )

    client.post("/api/shopping-list/add", json={"recipe_id": recipe["id"]}, headers=auth_headers)

    captured = {}

    def fake_categorize(ingredients):
        captured["ingredients"] = ingredients
        return {"Warzywa i owoce": [], "Nabiał": [], "Mięso i ryby": [], "Przyprawy i sosy": [], "Inne": []}

    with patch("app.routers.shopping_lists.categorize_ingredients", side_effect=fake_categorize):
        client.get("/api/shopping-list/", headers=auth_headers)

    # Original label should remain unchanged
    assert "2 ząbki czosnek" in captured["ingredients"]
    assert "garlic powder" not in captured["ingredients"]
