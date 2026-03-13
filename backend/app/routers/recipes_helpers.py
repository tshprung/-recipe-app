"""Shared helpers for recipe ownership, listing, and ingredient matching. Used by recipes router."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .. import models


def _recipe_owned_by(
    recipe: models.Recipe,
    current_user: models.User | None,
    trial_session: models.TrialSession | None,
) -> bool:
    if current_user is not None and recipe.user_id == current_user.id:
        return True
    if trial_session is not None and recipe.trial_session_id == trial_session.id:
        return True
    return False


def get_recipe_or_404(
    recipe_id: int,
    current_user: models.User | None,
    trial_session: models.TrialSession | None,
    db: Session,
) -> models.Recipe:
    """Return recipe if found and owned by user or trial; else raise 404."""
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or not _recipe_owned_by(recipe, current_user, trial_session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


def recipes_for_user_or_trial(
    db: Session,
    current_user: models.User | None,
    trial_session: models.TrialSession | None,
) -> list[models.Recipe]:
    """Return recipes belonging to the current user or trial session. Caller must check auth."""
    if current_user is not None:
        return db.query(models.Recipe).filter(models.Recipe.user_id == current_user.id).all()
    return db.query(models.Recipe).filter(models.Recipe.trial_session_id == trial_session.id).all()


def recipe_matches_query(recipe: models.Recipe, q: str) -> bool:
    """True if recipe title, ingredients, or tags contain the query (case-insensitive)."""
    if not q or not recipe:
        return True
    q_lower = q.strip().lower()
    if not q_lower:
        return True
    if q_lower in (recipe.title_pl or "").lower():
        return True
    if q_lower in (recipe.title_original or "").lower():
        return True
    ingredients_pl = recipe.ingredients_pl or []
    ing_parts = []
    for item in ingredients_pl:
        if isinstance(item, str):
            ing_parts.append(item)
        elif isinstance(item, dict):
            ing_parts.append(str(item.get("name", "")) + " " + str(item.get("amount", "")))
        else:
            ing_parts.append(str(item))
    if q_lower in " ".join(ing_parts).lower():
        return True
    tags = recipe.tags or []
    if q_lower in " ".join(str(t) for t in tags).lower():
        return True
    return False


COMMON_PANTRY = {
    "salt", "sugar", "pepper", "black pepper", "oil", "olive oil", "vegetable oil",
    "water", "flour", "vanilla", "vinegar", "baking powder", "baking soda",
    "soy sauce", "paprika", "cumin", "oregano", "basil", "garlic", "onion",
    "butter", "milk", "eggs", "honey", "mustard", "ketchup",
}


def normalize_ingredient_line(item) -> str:
    """Extract a single line of text from an ingredient (string or dict)."""
    if isinstance(item, str):
        return (item or "").strip()
    if isinstance(item, dict):
        return f"{item.get('amount', '')} {item.get('name', '')}".strip()
    return str(item).strip()


def recipe_ingredient_lines(recipe: models.Recipe) -> list[str]:
    """List of normalized ingredient lines for a recipe (from ingredients_pl)."""
    lines = []
    for item in recipe.ingredients_pl or []:
        line = normalize_ingredient_line(item)
        if line:
            lines.append(line.lower())
    return lines


def user_ingredients_set(ingredients: list[str], assume_pantry: bool) -> set[str]:
    """Set of normalized user ingredient strings (plus pantry if assumed)."""
    out = set()
    for s in ingredients or []:
        t = (s or "").strip().lower()
        if t:
            out.add(t)
    if assume_pantry:
        out |= COMMON_PANTRY
    return out


def ingredient_matches_user(recipe_line: str, user_set: set[str]) -> bool:
    """True if recipe_line is 'covered' by any user ingredient (substring or exact)."""
    recipe_lower = recipe_line.lower()
    for u in user_set:
        if u in recipe_lower or recipe_lower in u:
            return True
    for word in recipe_lower.replace(",", " ").split():
        word = word.strip()
        if len(word) < 3:
            continue
        for u in user_set:
            if word in u or u in word:
                return True
    return False


def recipe_meat_dairy_keywords(recipe: models.Recipe) -> tuple[bool, bool]:
    """Returns (has_meat, has_dairy) based on ingredient text."""
    text = " ".join(recipe_ingredient_lines(recipe)).lower()
    meat = any(w in text for w in (
        "meat", "chicken", "beef", "pork", "lamb", "fish", "salmon", "tuna",
        "mięso", "kurczak", "wołowina", "wieprzowina", "ryba", "łosoś",
    ))
    dairy = any(w in text for w in (
        "milk", "cream", "cheese", "butter", "yogurt",
        "mleko", "śmietana", "ser", "masło", "jogurt",
    ))
    return meat, dairy


def what_can_i_make_my_recipes(
    recipes: list[models.Recipe],
    user_ingredients: list[str],
    assume_pantry: bool,
    diet_filters: list[str] | None,
) -> list[tuple[models.Recipe, bool, list[str]]]:
    """Returns list of (recipe, can_make, missing_ingredients) sorted by best match."""
    user_set = user_ingredients_set(user_ingredients, assume_pantry)
    results = []
    for recipe in recipes:
        lines = recipe_ingredient_lines(recipe)
        if not lines:
            continue
        if diet_filters:
            meat, dairy = recipe_meat_dairy_keywords(recipe)
            if "vegetarian" in diet_filters or "vegan" in diet_filters:
                if meat:
                    continue
            if "dairy_free" in diet_filters and dairy:
                continue
        missing = []
        for line in lines:
            if not ingredient_matches_user(line, user_set):
                missing.append(line)
        can_make = len(missing) == 0
        results.append((recipe, can_make, missing))
    results.sort(key=lambda x: (not x[1], len(x[2]), -len(recipe_ingredient_lines(x[0]))))
    return results


def normalize_adapt_types(variant_types: list[str] | None, variant_type: str | None) -> list[str]:
    """Normalize adapt request variant types to a list."""
    if variant_types:
        return list(variant_types)
    return [variant_type] if variant_type else []
