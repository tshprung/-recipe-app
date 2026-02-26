from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.adaptation import adapt_recipe
from ..services.translation import translate_recipe

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.post("/", response_model=schemas.RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: schemas.RecipeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        translated = translate_recipe(
            raw_input=payload.raw_input,
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
        raw_input=payload.raw_input,
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

    try:
        result = adapt_recipe(recipe, payload.variant_type)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Adaptation failed: {e}")

    if result.get("can_adapt"):
        variant = models.RecipeVariant(
            recipe_id=recipe_id,
            variant_type=payload.variant_type,
            title_pl=result["title_pl"],
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
