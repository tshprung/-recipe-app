from unittest.mock import patch

from app import models
from app.services.what_can_i_make_ai import recipe_complies_with_allergens, recipe_complies_with_diets
from .conftest import TestSessionLocal, password_hash, CAPTCHA_DUMMY


def test_recipe_complies_with_diets_kosher_rejects_meat_and_dairy():
    """Kosher filter must reject recipes that mix meat and dairy."""
    recipe = {
        "title": "Kosher meatballs",
        "ingredients": ["ground beef", "parmesan cheese", "egg", "breadcrumbs"],
        "steps": ["Mix beef with cheese and bake"],
    }
    assert recipe_complies_with_diets(recipe, ["kosher"]) is False


def test_recipe_complies_with_diets_kosher_accepts_vegetarian():
    recipe = {
        "title": "Vegetarian pasta",
        "ingredients": ["pasta", "tomatoes", "basil", "olive oil"],
        "steps": ["Cook pasta", "Toss with sauce"],
    }
    assert recipe_complies_with_diets(recipe, ["kosher"]) is True


def test_recipe_complies_with_diets_kosher_rejects_pork():
    recipe = {
        "title": "Pork chops",
        "ingredients": ["pork chops", "salt", "pepper"],
        "steps": ["Fry the pork"],
    }
    assert recipe_complies_with_diets(recipe, ["kosher"]) is False


def test_recipe_complies_with_diets_for_kids_under_1_rejects_tacos():
    """For kids under 1 must reject adult-style dishes like tacos."""
    recipe = {
        "title": "Beef Tacos with Avocado",
        "ingredients": ["ground beef", "taco shells", "avocado"],
        "steps": ["Cook beef", "Fill tacos"],
    }
    assert recipe_complies_with_diets(recipe, ["for_kids_under_1"]) is False


def test_recipe_complies_with_diets_for_kids_under_1_rejects_honey():
    recipe = {
        "title": "Oatmeal for baby",
        "ingredients": ["oatmeal", "honey", "banana"],
        "steps": ["Mix and serve"],
    }
    assert recipe_complies_with_diets(recipe, ["for_kids_under_1"]) is False


def test_recipe_complies_with_diets_for_kids_under_1_accepts_puree():
    recipe = {
        "title": "Simple carrot puree for baby",
        "ingredients": ["carrots", "water"],
        "steps": ["Steam and blend until smooth"],
    }
    assert recipe_complies_with_diets(recipe, ["for_kids_under_1"]) is True


def test_recipe_complies_with_diets_for_kids_rejects_wine():
    recipe = {
        "title": "Coq au vin",
        "ingredients": ["chicken", "red wine", "mushrooms"],
        "steps": ["Simmer with wine"],
    }
    assert recipe_complies_with_diets(recipe, ["for_kids"]) is False


def test_recipe_complies_with_diets_for_kids_accepts_pasta():
    recipe = {
        "title": "Pasta with tomato sauce",
        "ingredients": ["pasta", "tomatoes", "basil"],
        "steps": ["Cook pasta", "Toss with sauce"],
    }
    assert recipe_complies_with_diets(recipe, ["for_kids"]) is True


def test_recipe_complies_with_allergens_milk_rejects_cheese():
    """Milk allergen must reject recipes containing cheese (dairy)."""
    recipe = {
        "title": "Classic Margherita Pizza",
        "ingredients": ["200 g fresh mozzarella cheese, sliced", "tomatoes", "basil"],
        "steps": ["Add cheese and bake"],
    }
    assert recipe_complies_with_allergens(recipe, ["milk"], None) is False


def test_recipe_complies_with_allergens_milk_rejects_optional_milk():
    """Milk allergen must reject even when milk is listed as optional (e.g. water or milk)."""
    recipe = {
        "title": "Classic Oatmeal",
        "ingredients": ["100 g rolled oats", "500 ml water or milk", "1 pinch salt"],
        "steps": ["Bring water or milk to boil", "Add oats"],
    }
    assert recipe_complies_with_allergens(recipe, ["milk"], None) is False


def test_recipe_complies_with_allergens_milk_accepts_no_dairy():
    recipe = {
        "title": "Vegan lentil soup",
        "ingredients": ["lentils", "onion", "carrots", "vegetable stock"],
        "steps": ["Simmer until tender"],
    }
    assert recipe_complies_with_allergens(recipe, ["milk"], None) is True


def test_recipe_complies_with_allergens_custom_avoid_rejects():
    """Custom avoid terms must cause rejection when they appear in the recipe."""
    recipe = {
        "title": "Kiwi smoothie",
        "ingredients": ["kiwi", "banana", "orange juice"],
        "steps": ["Blend kiwi with banana"],
    }
    assert recipe_complies_with_allergens(recipe, None, ["kiwi"]) is False


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

    # Mock AI suggestions: two vegetarian recipes; both pass diet filter, endpoint returns up to 3.
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
    assert len(data["suggestions"]) >= 1
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

