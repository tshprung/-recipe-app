"""Tests for recipe adaptation (vegetarian / vegan / kosher etc.)."""
from unittest.mock import patch


MOCK_VARIANT = {
    "can_adapt": True,
    "title_pl": "Zupa Pomidorowa (wersja wegetariańska)",
    "ingredients_pl": ["500g pomidory", "1 cebula", "2 ząbki czosnek"],
    "steps_pl": ["Podsmaż cebulę.", "Dodaj pomidory.", "Gotuj 20 min."],
    "notes": {},
    "alternatives": [],
}

MOCK_CANNOT_ADAPT = {
    "can_adapt": False,
    "title_pl": None,
    "ingredients_pl": [],
    "steps_pl": [],
    "notes": {},
    "alternatives": [
        {
            "title": "Wersja z rybą",
            "reason": "Ryba dobrze zastępuje mięso.",
            "instruction": "Replace all meat with salmon.",
        },
        {
            "title": "Wersja z tofu",
            "reason": "Tofu jest dobrym zamiennikiem białka.",
            "instruction": "Replace all meat with firm tofu.",
        },
    ],
}


def test_list_variants_empty(client, auth_headers, recipe):
    r = client.get(f"/api/recipes/{recipe['id']}/variants", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_adapt_recipe_vegetarian(client, auth_headers, recipe):
    with patch("app.routers.recipes.adapt_recipe", return_value=MOCK_VARIANT):
        r = client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegetarian"},
            headers=auth_headers,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["can_adapt"] is True
    assert data["variant"]["variant_type"] == "vegetarian"
    assert data["variant"]["title_pl"] == "Zupa Pomidorowa (wersja wegetariańska)"
    assert len(data["variant"]["ingredients_pl"]) == 3


def test_adapt_recipe_variant_saved_to_db(client, auth_headers, recipe):
    with patch("app.routers.recipes.adapt_recipe", return_value=MOCK_VARIANT):
        client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegetarian"},
            headers=auth_headers,
        )

    r = client.get(f"/api/recipes/{recipe['id']}/variants", headers=auth_headers)
    assert r.status_code == 200
    variants = r.json()
    assert len(variants) == 1
    assert variants[0]["variant_type"] == "vegetarian"


def test_adapt_recipe_second_call_uses_cache(client, auth_headers, recipe):
    """Second /adapt call for the same type must NOT call adapt_recipe again."""
    with patch("app.routers.recipes.adapt_recipe", return_value=MOCK_VARIANT) as mock_fn:
        client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegetarian"},
            headers=auth_headers,
        )
        client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegetarian"},
            headers=auth_headers,
        )
    assert mock_fn.call_count == 1


def test_adapt_recipe_cannot_adapt_returns_alternatives(client, auth_headers, recipe):
    with patch("app.routers.recipes.adapt_recipe", return_value=MOCK_CANNOT_ADAPT):
        r = client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegan"},
            headers=auth_headers,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["can_adapt"] is False
    assert data["variant"] is None
    assert len(data["alternatives"]) == 2
    assert data["alternatives"][0]["title"] == "Wersja z rybą"


def test_adapt_recipe_cannot_adapt_does_not_save_variant(client, auth_headers, recipe):
    with patch("app.routers.recipes.adapt_recipe", return_value=MOCK_CANNOT_ADAPT):
        client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegan"},
            headers=auth_headers,
        )
    r = client.get(f"/api/recipes/{recipe['id']}/variants", headers=auth_headers)
    assert r.json() == []


def test_adapt_recipe_with_custom_instruction(client, auth_headers, recipe):
    custom_variant = {**MOCK_VARIANT, "title_pl": "Zupa z łososiem"}
    with patch("app.routers.recipes.adapt_recipe", return_value=custom_variant):
        r = client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={
                "variant_type": "vegan",
                "custom_instruction": "Replace all meat with salmon.",
                "custom_title": "Wersja z łososiem",
            },
            headers=auth_headers,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["can_adapt"] is True
    # custom variants get an _alt suffix
    assert data["variant"]["variant_type"].startswith("vegan_alt")
    assert data["variant"]["title_pl"] == "Wersja z łososiem"


def test_adapt_recipe_multiple_custom_variants_get_unique_slugs(client, auth_headers, recipe):
    custom_variant = {**MOCK_VARIANT, "title_pl": "Custom"}
    with patch("app.routers.recipes.adapt_recipe", return_value=custom_variant):
        r1 = client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegan", "custom_instruction": "Use salmon."},
            headers=auth_headers,
        )
        r2 = client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegan", "custom_instruction": "Use tofu."},
            headers=auth_headers,
        )
    assert r1.json()["variant"]["variant_type"] != r2.json()["variant"]["variant_type"]


def test_adapt_recipe_not_found(client, auth_headers):
    r = client.post(
        "/api/recipes/99999/adapt",
        json={"variant_type": "vegetarian"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_variants_deleted_with_recipe(client, auth_headers, recipe):
    with patch("app.routers.recipes.adapt_recipe", return_value=MOCK_VARIANT):
        client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegetarian"},
            headers=auth_headers,
        )
    client.delete(f"/api/recipes/{recipe['id']}", headers=auth_headers)
    # Recipe is gone; attempting to list variants returns 404
    r = client.get(f"/api/recipes/{recipe['id']}/variants", headers=auth_headers)
    assert r.status_code == 404
