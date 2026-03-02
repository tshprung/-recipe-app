"""Tests for recipe adaptation (vegetarian / vegan / kosher etc.)."""
import json
from unittest.mock import MagicMock, patch


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


# ---------------------------------------------------------------------------
# New tests from work.txt
# ---------------------------------------------------------------------------

def test_vegan_adaptation_with_eggs_flagged_in_notes(client, auth_headers, recipe):
    """
    When the adaptation model cannot substitute eggs in a vegan recipe, it must either
    remove the eggs from ingredients_pl OR keep them and add a warning note.
    The API must pass this information through unchanged.
    """
    vegan_with_flagged_eggs = {
        "can_adapt": True,
        "title_pl": "Jajecznica wegańska",
        "ingredients_pl": ["3 jajka"],        # eggs kept — no replacement found
        "steps_pl": ["Podsmaż."],
        "notes": {
            "ostrzeżenia": [
                "Nie znaleziono zamiennika dla: 3 jajka. Rozważ pominięcie."
            ]
        },
        "alternatives": [],
    }
    with patch("app.routers.recipes.adapt_recipe", return_value=vegan_with_flagged_eggs):
        r = client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegan"},
            headers=auth_headers,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["can_adapt"] is True
    variant = data["variant"]
    ingredients_text = " ".join(str(i) for i in variant["ingredients_pl"])
    warnings = variant["notes"].get("ostrzeżenia", [])
    # Either eggs were replaced (not in list) OR a warning note exists
    eggs_present = "jajka" in ingredients_text or "jajko" in ingredients_text
    assert not eggs_present or len(warnings) > 0, (
        "Eggs are present in ingredients_pl but no warning note was added"
    )


def test_vegan_adaptation_variant_type_saved_as_vegan(client, auth_headers, recipe):
    """variant_type must be saved exactly as 'vegan' in recipe_variants table."""
    with patch("app.routers.recipes.adapt_recipe", return_value=MOCK_VARIANT):
        r = client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegan"},
            headers=auth_headers,
        )
    assert r.status_code == 200
    assert r.json()["variant"]["variant_type"] == "vegan"

    # Verify via the variants list endpoint
    r = client.get(f"/api/recipes/{recipe['id']}/variants", headers=auth_headers)
    assert r.json()[0]["variant_type"] == "vegan"


def test_original_recipe_has_no_variant_type_field(client, auth_headers, recipe):
    """GET /recipes/{id} returns a recipe object (no variant_type) — it IS the original."""
    r = client.get(f"/api/recipes/{recipe['id']}", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    # Original recipes don't have variant_type; variants do
    assert "variant_type" not in data
    assert data["title_pl"] == "Zupa Pomidorowa"


def test_variant_badge_type_matches_request(client, auth_headers, recipe):
    """Each variant's variant_type field matches what was requested."""
    for vtype in ("vegetarian", "dairy_free"):
        adapted = {**MOCK_VARIANT, "title_pl": f"Wersja {vtype}"}
        with patch("app.routers.recipes.adapt_recipe", return_value=adapted):
            r = client.post(
                f"/api/recipes/{recipe['id']}/adapt",
                json={"variant_type": vtype},
                headers=auth_headers,
            )
        assert r.json()["variant"]["variant_type"] == vtype

    variants = client.get(
        f"/api/recipes/{recipe['id']}/variants", headers=auth_headers
    ).json()
    types = {v["variant_type"] for v in variants}
    assert "vegetarian" in types
    assert "dairy_free" in types


def test_adapt_recipe_with_curly_braces_in_data():
    """
    Regression: recipe data containing { } must never raise
    'Single } encountered in format string' (or any format error).
    Previously broke because str.format() was used with un-escaped user data.
    Now uses string.Template which treats { } as literals.
    """
    from app.services.adaptation import adapt_recipe

    class MockRecipe:
        title_pl = "Przepis {specjalny} z {nawiasami}"
        ingredients_pl = [
            {"amount": "2 {sztuki}", "name": "jajka {duże, rozmiar L}"},
            "100g mąki {pszennej}",
            "1 łyżka sosu {sojowego}",
        ]
        steps_pl = [
            "Krok {1}: wymieszaj {składniki} razem.",
            "Krok {2}: piecz w {180}°C przez 30 minut.",
        ]

    mock_response = json.dumps({
        "can_adapt": True,
        "title_pl": "Przepis wegański",
        "ingredients_pl": ["2 sztuki tofu", "100g mąki", "1 łyżka sosu sojowego"],
        "steps_pl": ["Krok 1: wymieszaj.", "Krok 2: piecz."],
        "notes": {"ostrzeżenia": []},
        "alternatives": [],
    })
    mock_msg = MagicMock()
    mock_msg.choices = [MagicMock(message=MagicMock(content=mock_response))]

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with patch("app.services.adaptation.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_msg
            MockOpenAI.return_value = mock_client

            # Must not raise any format/template error
            result = adapt_recipe(MockRecipe(), "vegan")

    assert result["can_adapt"] is True


def test_adapt_recipe_without_openai_key_returns_503(client, auth_headers, recipe):
    """POST /api/recipes/{id}/adapt must return 503 when OPENAI_API_KEY is missing.
    Regression: the missing key error was surfaced as an unhandled 500."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
        r = client.post(
            f"/api/recipes/{recipe['id']}/adapt",
            json={"variant_type": "vegetarian"},
            headers=auth_headers,
        )
    assert r.status_code == 503
    assert "OPENAI_API_KEY" in r.json()["detail"]


def test_variants_route_returns_401_not_404_unauthenticated(client):
    """GET /api/recipes/{id}/variants must be a registered route.
    Unauthenticated requests return 401 (auth required), not 404 (route missing).
    Regression: stale uvicorn processes from an older code version served 404."""
    r = client.get("/api/recipes/1/variants")
    assert r.status_code == 401


def test_adapt_prompt_contains_correct_diet_instructions(auth_headers):
    """
    adapt_recipe() must send a prompt to the model that includes:
    - the diet label (e.g. 'wegańskim')
    - the flagging rule keyword ('ostrzeżenia')
    - the 'Nie znaleziono' warning language
    """
    from app.services.adaptation import adapt_recipe

    class MockRecipe:
        title_pl = "Jajecznica z boczkiem"
        ingredients_pl = [
            {"amount": "3 sztuki", "name": "jajka"},
            {"amount": "100g", "name": "boczek"},
        ]
        steps_pl = ["Ubij jajka.", "Podsmaż boczek.", "Połącz składniki."]

    mock_response_body = json.dumps({
        "can_adapt": True,
        "title_pl": "Jajecznica wegańska",
        "ingredients_pl": ["tofu scramble", "boczek wegański"],
        "steps_pl": ["Pokrusz tofu.", "Podsmaż."],
        "notes": {"ostrzeżenia": []},
        "alternatives": [],
    })

    captured = {}

    def fake_create(model, messages, response_format, max_tokens, temperature):
        captured["system"] = next(
            (m["content"] for m in messages if m["role"] == "system"), ""
        )
        captured["prompt"] = next(
            (m["content"] for m in messages if m["role"] == "user"), ""
        )
        mock_msg = MagicMock()
        mock_msg.choices = [MagicMock(message=MagicMock(content=mock_response_body))]
        return mock_msg

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with patch("app.services.adaptation.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = fake_create
            MockOpenAI.return_value = mock_client

            adapt_recipe(MockRecipe(), "vegan")

    prompt = captured["prompt"]
    assert "wegańskim" in prompt, "Prompt must contain the Polish diet label"
    assert "ostrzeżenia" in prompt, "Prompt must mention the 'ostrzeżenia' notes key"
    assert "Nie znaleziono" in prompt, "Prompt must include the flagging warning language"
