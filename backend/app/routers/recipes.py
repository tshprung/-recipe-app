from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
import re

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.adaptation import adapt_recipe
from ..services.translation import translate_recipe

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize_text(text: str, max_len: int | None = None) -> str:
    cleaned = _TAG_RE.sub("", text or "")
    cleaned = cleaned.strip()
    if max_len is not None:
        cleaned = cleaned[:max_len]
    return cleaned


@router.post("/", response_model=schemas.RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: schemas.RecipeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Zweryfikuj swój email przed użyciem aplikacji",
        )

    # Quota check (before OpenAI)
    user_for_update = (
        db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
    )
    if user_for_update.transformations_limit != -1 and (
        user_for_update.transformations_used >= user_for_update.transformations_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Wykorzystałeś limit darmowych przepisów. Skontaktuj się z administratorem.",
        )

    user_for_update.transformations_used += 1
    db.commit()

    raw_input = _sanitize_text(payload.raw_input, max_len=10000)

    try:
        translated = translate_recipe(
            raw_input=raw_input,
            target_city=current_user.target_city,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Translation failed: {e}")

    recipe = models.Recipe(
        user_id=current_user.id,
        title_pl=translated.get("title_pl", "Brak tytułu"),
        title_original=translated.get("title_original", payload.raw_input[:100]),
        ingredients_pl=translated.get("ingredients_pl", []),
        ingredients_original=translated.get("ingredients_original", []),
        steps_pl=translated.get("steps_pl", []),
        tags=translated.get("tags", []),
        substitutions=translated.get("substitutions", {}),
        notes=translated.get("notes", {}),
        raw_input=raw_input,
        source_language=current_user.source_language,
        source_country=current_user.source_country,
        target_language=current_user.target_language,
        target_country=current_user.target_country,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("/", response_model=list[schemas.RecipeOut])
def list_recipes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Recipe).filter(models.Recipe.user_id == current_user.id).all()


@router.get("/{recipe_id}", response_model=schemas.RecipeOut)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


@router.patch("/{recipe_id}/notes", response_model=schemas.RecipeOut)
def update_notes(
    recipe_id: int,
    payload: schemas.RecipeUserNotesUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    recipe.user_notes = payload.user_notes
    db.commit()
    db.refresh(recipe)
    return recipe


@router.patch("/{recipe_id}/favorite", response_model=schemas.RecipeOut)
def toggle_favorite(
    recipe_id: int,
    payload: schemas.RecipeFavoriteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    recipe.is_favorite = payload.is_favorite
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("/{recipe_id}/variants", response_model=list[schemas.RecipeVariantOut])
def list_variants(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe.variants


@router.post("/{recipe_id}/adapt")
def adapt_recipe_endpoint(
    recipe_id: int,
    payload: schemas.AdaptRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Zweryfikuj swój email przed użyciem aplikacji",
        )

    # Quota check (before OpenAI)
    user_for_update = (
        db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
    )
    if user_for_update.transformations_limit != -1 and (
        user_for_update.transformations_used >= user_for_update.transformations_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Wykorzystałeś limit darmowych przepisów. Skontaktuj się z administratorem.",
        )

    user_for_update.transformations_used += 1
    db.commit()

    # For standard (non-custom) adaptations, check cache first
    if not payload.custom_instruction:
        existing = (
            db.query(models.RecipeVariant)
            .filter_by(recipe_id=recipe_id, variant_type=payload.variant_type)
            .first()
        )
        if existing:
            return {
                "can_adapt": True,
                "variant": schemas.RecipeVariantOut.model_validate(existing),
                "alternatives": [],
            }

    custom_instruction = (
        _sanitize_text(payload.custom_instruction, max_len=1000)
        if payload.custom_instruction is not None
        else None
    )

    try:
        result = adapt_recipe(recipe, payload.variant_type, custom_instruction)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Adaptation failed: {e}")

    if result.get("can_adapt"):
        # For custom alternatives, build a unique variant_type slug
        if payload.custom_instruction:
            existing_count = (
                db.query(models.RecipeVariant)
                .filter(
                    models.RecipeVariant.recipe_id == recipe_id,
                    models.RecipeVariant.variant_type.like(f"{payload.variant_type}_alt%"),
                )
                .count()
            )
            variant_type = f"{payload.variant_type}_alt{existing_count}"
        else:
            variant_type = payload.variant_type

        title_pl = payload.custom_title or result["title_pl"]

        variant = models.RecipeVariant(
            recipe_id=recipe_id,
            variant_type=variant_type,
            title_pl=title_pl,
            ingredients_pl=result["ingredients_pl"],
            steps_pl=result["steps_pl"],
            notes=result.get("notes", {}),
        )
        db.add(variant)
        db.commit()
        db.refresh(variant)
        return {
            "can_adapt": True,
            "variant": schemas.RecipeVariantOut.model_validate(variant),
            "alternatives": [],
        }
    else:
        return {
            "can_adapt": False,
            "variant": None,
            "alternatives": result.get("alternatives", []),
        }


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    # Remove from any shopping lists before deleting the recipe
    db.query(models.ShoppingListRecipe).filter(
        models.ShoppingListRecipe.recipe_id == recipe_id
    ).delete()
    db.delete(recipe)
    db.commit()
