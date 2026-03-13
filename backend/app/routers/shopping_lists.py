from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.categorization import CATEGORIES, categorize_ingredients
from ..services.email import send_shopping_list_email
from ..services.shopping_list_ingredients import (
    aggregate_ingredients,
    normalize_ingredient_for_shopping,
    strip_cooking_instructions,
)

_EMPTY_ITEMS = {cat: [] for cat in CATEGORIES}


def _invalidate_shopping_list_cache(user_id: int, db: Session) -> None:
    """Remove cached shopping list for this user so next GET recomputes."""
    db.query(models.ShoppingListCache).filter(
        models.ShoppingListCache.user_id == user_id
    ).delete(synchronize_session=False)

router = APIRouter(prefix="/api/shopping-list", tags=["shopping-list"])


def _get_recipe_ids(user_id: int, db: Session) -> list[int]:
    records = (
        db.query(models.ShoppingListRecipe)
        .join(models.Recipe, models.ShoppingListRecipe.recipe_id == models.Recipe.id)
        .filter(models.ShoppingListRecipe.user_id == user_id)
        .order_by(models.ShoppingListRecipe.added_at)
        .all()
    )
    seen: set[int] = set()
    result: list[int] = []
    for r in records:
        if r.recipe_id not in seen:
            seen.add(r.recipe_id)
            result.append(r.recipe_id)
    return result


def _apply_substitutions(label: str, user: models.User, db: Session) -> str:
    row = (
        db.query(models.IngredientSubstitution)
        .filter(
            models.IngredientSubstitution.target_country == user.target_country,
            func.lower(models.IngredientSubstitution.ingredient_name) == label.lower(),
        )
        .first()
    )
    return row.substitution if row else label


def _collect_ingredients(recipe_ids: list[int], user_id: int, db: Session, user: models.User | None = None) -> list[str]:
    recipes = (
        db.query(models.Recipe)
        .filter(
            models.Recipe.id.in_(recipe_ids),
            models.Recipe.user_id == user_id,
        )
        .all()
    )
    ingredients: list[str] = []
    for recipe in recipes:
        for ing in recipe.ingredients_pl or []:
            if isinstance(ing, dict):
                amount, name = normalize_ingredient_for_shopping(
                    ing.get("amount", ""), ing.get("name", "")
                )
                label = f"{amount} {name}".strip()
            else:
                label = strip_cooking_instructions(str(ing)).strip()
            if label:
                if user is not None:
                    label = _apply_substitutions(label, user, db)
                ingredients.append(label)
    # Merge same ingredient and sum quantities (e.g. "1 egg" + "1 egg" → "2 eggs")
    return aggregate_ingredients(ingredients)


# --- GET /recipes — cheap, no OpenAI, just returns which recipes are in the list ---

@router.get("/recipes", response_model=schemas.ShoppingListRecipeIdsOut)
def get_recipe_ids(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return {"recipe_ids": _get_recipe_ids(current_user.id, db)}


# --- GET / — full list with merged+categorized ingredients ---

@router.get("/", response_model=schemas.ShoppingListOut)
def get_shopping_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe_ids = _get_recipe_ids(current_user.id, db)
    if not recipe_ids:
        _invalidate_shopping_list_cache(current_user.id, db)
        return {"recipe_ids": [], "items": _EMPTY_ITEMS.copy()}

    snapshot = sorted(recipe_ids)
    # We cannot reliably compare JSON arrays directly in Postgres (no json = json operator in some setups),
    # so fetch this user's cache rows and match the snapshot in Python.
    cached_rows = (
        db.query(models.ShoppingListCache)
        .filter(models.ShoppingListCache.user_id == current_user.id)
        .order_by(models.ShoppingListCache.updated_at.desc())
        .all()
    )
    cached = next((row for row in cached_rows if row.recipe_ids_snapshot == snapshot), None)
    if cached:
        return {"recipe_ids": recipe_ids, "items": cached.items}

    ingredients = _collect_ingredients(recipe_ids, current_user.id, db, user=current_user)
    if not ingredients:
        return {"recipe_ids": recipe_ids, "items": _EMPTY_ITEMS.copy()}

    try:
        items = categorize_ingredients(ingredients)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Categorization failed: {e}")

    # Post-process: strip any prep/usage phrases the categorizer may have re-added
    for cat in list(items.keys()):
        raw = items.get(cat)
        if not isinstance(raw, list):
            items[cat] = []
            continue
        items[cat] = [
            cleaned for s in raw
            if isinstance(s, str) and (cleaned := strip_cooking_instructions(s).strip())
        ]

    _invalidate_shopping_list_cache(current_user.id, db)
    db.add(
        models.ShoppingListCache(
            user_id=current_user.id,
            recipe_ids_snapshot=snapshot,
            items=items,
        )
    )
    db.commit()

    return {"recipe_ids": recipe_ids, "items": items}


# --- POST /add — add a recipe to the shopping list ---

@router.post("/add", response_model=schemas.ShoppingListRecipeIdsOut)
def add_recipe(
    payload: schemas.ShoppingListAddRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Verify recipe belongs to user
    recipe = db.get(models.Recipe, payload.recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Check not already in list
    exists = (
        db.query(models.ShoppingListRecipe)
        .filter(
            models.ShoppingListRecipe.user_id == current_user.id,
            models.ShoppingListRecipe.recipe_id == payload.recipe_id,
        )
        .first()
    )
    if not exists:
        entry = models.ShoppingListRecipe(
            user_id=current_user.id,
            recipe_id=payload.recipe_id,
        )
        db.add(entry)
        db.commit()
        _invalidate_shopping_list_cache(current_user.id, db)

    return {"recipe_ids": _get_recipe_ids(current_user.id, db)}


# --- DELETE /remove/{recipe_id} — remove a recipe from the shopping list ---

@router.delete("/remove/{recipe_id}", response_model=schemas.ShoppingListRecipeIdsOut)
def remove_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entry = (
        db.query(models.ShoppingListRecipe)
        .filter(
            models.ShoppingListRecipe.user_id == current_user.id,
            models.ShoppingListRecipe.recipe_id == recipe_id,
        )
        .first()
    )
    if entry:
        db.delete(entry)
        db.commit()
        _invalidate_shopping_list_cache(current_user.id, db)

    return {"recipe_ids": _get_recipe_ids(current_user.id, db)}


# --- DELETE /clear — remove all recipes from the shopping list ---

@router.delete("/clear", response_model=schemas.ShoppingListRecipeIdsOut)
def clear_shopping_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db.query(models.ShoppingListRecipe).filter(
        models.ShoppingListRecipe.user_id == current_user.id
    ).delete(synchronize_session=False)
    db.commit()
    _invalidate_shopping_list_cache(current_user.id, db)
    return {"recipe_ids": []}


# --- POST /email — send current shopping list to user's registered email ---

@router.post("/email")
def email_shopping_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe_ids = _get_recipe_ids(current_user.id, db)
    if not recipe_ids:
        raise HTTPException(status_code=400, detail="Shopping list is empty")

    ingredients = _collect_ingredients(recipe_ids, current_user.id, db, user=current_user)

    try:
        items = categorize_ingredients(ingredients)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Categorization failed: {e}")

    try:
        send_shopping_list_email(to_email=current_user.email, items=items)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to send email: {e}")

    return {"message": f"Email wysłany na adres {current_user.email}"}
