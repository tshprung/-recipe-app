import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user, create_access_token
from ..database import get_db
from ..services.starter_recipes import add_starter_recipes_to_user, ensure_starter_recipes_for_user

router = APIRouter(prefix="/api/users", tags=["users"])


def _admin_emails() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS") or ""
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    data = schemas.UserOut.model_validate(current_user).model_dump()
    data["is_admin"] = (current_user.email or "").strip().lower() in _admin_emails()
    # Sliding expiry: issue a new token on every visit so the counter resets
    data["renewed_token"] = create_access_token(current_user.id)
    return schemas.UserOut(**data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete the current user and all their data (recipes, shopping list entries)."""
    user_id = current_user.id

    # 1. Remove user's shopping list entries
    db.query(models.ShoppingListRecipe).filter(models.ShoppingListRecipe.user_id == user_id).delete()

    # 2. Delete user's recipes (RecipeVariant cascades via relationship)
    db.query(models.Recipe).filter(models.Recipe.user_id == user_id).delete()

    # 3. Unlink ingredient substitutions created by this user
    db.query(models.IngredientSubstitution).filter(
        models.IngredientSubstitution.created_by_user_id == user_id
    ).update({models.IngredientSubstitution.created_by_user_id: None})

    # 4. Delete the user
    db.delete(current_user)
    db.commit()
    return None


@router.patch("/me/settings", response_model=schemas.UserOut)
def update_settings(
    payload: schemas.UserSettings,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    for field, value in payload.model_dump().items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/claim-starter-recipes", status_code=status.HTTP_204_NO_CONTENT)
def claim_starter_recipes(
    payload: schemas.OnboardingClaimRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Claim pre-fetched starter recipes from onboarding and optionally apply onboarding profile.
    If claim_token is invalid or expired, returns 400.
    """
    row = (
        db.query(models.PreparedStarterRecipes)
        .filter(models.PreparedStarterRecipes.claim_token == payload.claim_token)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired claim token. You can add starter recipes from Settings.",
        )
    now = datetime.now(timezone.utc)
    if row.expires_at.tzinfo is None:
        row.expires_at = row.expires_at.replace(tzinfo=timezone.utc)
    if row.expires_at < now:
        db.delete(row)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claim token expired. You can add starter recipes from Settings.",
        )
    # Apply optional profile updates from onboarding
    if payload.ui_language is not None:
        current_user.ui_language = payload.ui_language
    if payload.target_language is not None:
        current_user.target_language = payload.target_language
    if payload.target_country is not None:
        current_user.target_country = payload.target_country
    if payload.target_city is not None:
        current_user.target_city = payload.target_city
    if payload.target_zip is not None:
        current_user.target_zip = payload.target_zip
    if payload.dish_preferences is not None:
        current_user.dish_preferences = payload.dish_preferences
    if payload.household_adults is not None:
        current_user.household_adults = payload.household_adults
    if payload.household_kids is not None:
        current_user.household_kids = payload.household_kids
    if payload.diet_filters is not None:
        current_user.diet_filters = payload.diet_filters
    if payload.default_servings is not None:
        current_user.default_servings = payload.default_servings
    if payload.allergens is not None:
        current_user.allergens = payload.allergens
    if payload.custom_allergens_text is not None:
        current_user.custom_allergens_text = payload.custom_allergens_text
    db.commit()
    # Attach pre-fetched recipes to user (only if user has no recipes yet)
    if not current_user.starter_recipes_added:
        count = db.query(models.Recipe).filter(models.Recipe.user_id == current_user.id).count()
        if count == 0:
            add_starter_recipes_to_user(
                current_user, row.recipes_data, db,
                diet_filters=payload.diet_filters or None,
            )
    db.delete(row)
    db.commit()
    return None


@router.post("/me/fetch-starter-recipes", status_code=status.HTTP_204_NO_CONTENT)
def fetch_starter_recipes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Add 3 starter recipes from famous cooks (country/language) if the user has none.
    No-op if they already have recipes. Used from Settings when onboarding pre-fetch failed or was skipped.
    """
    ensure_starter_recipes_for_user(current_user, db)
    return None
