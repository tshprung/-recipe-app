import ipaddress
import re
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.adaptation import adapt_recipe
from ..services.translation import translate_recipe

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

_TAG_RE = re.compile(r"<[^>]+>")
_MAX_FETCH_BYTES = 500 * 1024  # 500 KB
_MIN_EXTRACTED_LEN = 10


def _sanitize_text(text: str, max_len: int | None = None) -> str:
    cleaned = _TAG_RE.sub("", text or "")
    cleaned = cleaned.strip()
    if max_len is not None:
        cleaned = cleaned[:max_len]
    return cleaned


def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").strip().lower()
    if host in ("localhost", "127.0.0.1", "::1", ""):
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            return False
    except ValueError:
        pass
    return True


def _fetch_and_extract_text(url: str) -> str:
    if not _is_safe_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or disallowed URL. Only public http(s) URLs are allowed.",
        )
    try:
        resp = httpx.get(
            url,
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "RecipeApp/1.0"},
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch page: {e.response.status_code}",
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to connect to the provided URL.",
        ) from e

    content = resp.content
    if len(content) > _MAX_FETCH_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page is too large to process.",
        )

    text = resp.text
    # Strip script/style and get visible text (simple approach)
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = _sanitize_text(text, max_len=10000)
    if len(text) < _MIN_EXTRACTED_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract recipe text from the provided URL.",
        )
    return text


@router.post("/", response_model=schemas.RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: schemas.RecipeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )

    if (payload.source_url or "").strip():
        raw_input = _fetch_and_extract_text(payload.source_url.strip())
    else:
        raw_input = _sanitize_text(payload.raw_input or "", max_len=10000)

    # Quota check (before OpenAI cost, but do not consume quota yet)
    user_for_update = (
        db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
    )
    if user_for_update.transformations_limit != -1 and (
        user_for_update.transformations_used >= user_for_update.transformations_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You have reached the free recipes limit. Contact the administrator.",
        )

    try:
        translated = translate_recipe(
            raw_input=raw_input,
            target_language=current_user.target_language,
            target_country=current_user.target_country,
            target_city=current_user.target_city,
        )
    except ValueError as e:
        msg = str(e) or ""
        if msg.startswith("NOT_A_RECIPE:"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "This doesn't look like a recipe. Please paste the ingredients + steps, or try a different URL. "
                    "If you think this is a mistake, contact tshprung.us@gmail.com."
                ),
            )
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Translation failed: {e}")

    recipe = models.Recipe(
        user_id=current_user.id,
        title_pl=translated.get("title_pl", "Untitled"),
        title_original=translated.get("title_original", (raw_input or "")[:100]),
        ingredients_pl=translated.get("ingredients_pl", []),
        ingredients_original=translated.get("ingredients_original", []),
        steps_pl=translated.get("steps_pl", []),
        tags=translated.get("tags", []),
        substitutions=translated.get("substitutions", {}),
        notes=translated.get("notes", {}),
        raw_input=raw_input,
        detected_language=translated.get("detected_language"),
        target_language=current_user.target_language,
        target_country=current_user.target_country,
        target_city=current_user.target_city,
    )

    # Consume quota only for valid recipe creation
    user_for_update.transformations_used += 1

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


@router.post("/{recipe_id}/relocalize", response_model=schemas.RecipeOut)
def relocalize_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )

    # Quota check before OpenAI cost, but do not consume quota yet
    user_for_update = (
        db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
    )
    if user_for_update.transformations_limit != -1 and (
        user_for_update.transformations_used >= user_for_update.transformations_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You have reached the free recipes limit. Contact the administrator.",
        )

    try:
        translated = translate_recipe(
            raw_input=recipe.raw_input,
            target_language=current_user.target_language,
            target_country=current_user.target_country,
            target_city=current_user.target_city,
        )
    except ValueError as e:
        msg = str(e) or ""
        if msg.startswith("NOT_A_RECIPE:"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "This doesn't look like a recipe. If you think this is a mistake, "
                    "contact tshprung.us@gmail.com."
                ),
            )
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Translation failed: {e}")

    recipe.title_pl = translated.get("title_pl", recipe.title_pl)
    recipe.title_original = translated.get("title_original", recipe.title_original)
    recipe.ingredients_pl = translated.get("ingredients_pl", recipe.ingredients_pl)
    recipe.ingredients_original = translated.get("ingredients_original", recipe.ingredients_original)
    recipe.steps_pl = translated.get("steps_pl", recipe.steps_pl)
    recipe.tags = translated.get("tags", recipe.tags)
    recipe.substitutions = translated.get("substitutions", recipe.substitutions)
    recipe.notes = translated.get("notes", recipe.notes)
    recipe.detected_language = translated.get("detected_language", recipe.detected_language)
    recipe.target_language = current_user.target_language
    recipe.target_country = current_user.target_country
    recipe.target_city = current_user.target_city

    user_for_update.transformations_used += 1
    db.commit()
    db.refresh(recipe)
    return recipe


def _normalize_adapt_types(payload: schemas.AdaptRequest) -> list[str]:
    if payload.variant_types:
        return list(payload.variant_types)
    return [payload.variant_type] if payload.variant_type else []


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
            detail="Verify your email before using the app.",
        )

    types = _normalize_adapt_types(payload)
    composite_key = ",".join(types)

    user_for_update = (
        db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
    )

    # For standard (non-custom) adaptations, check cache first (don't consume quota)
    if not payload.custom_instruction:
        existing = (
            db.query(models.RecipeVariant)
            .filter_by(recipe_id=recipe_id, variant_type=composite_key)
            .first()
        )
        if existing:
            return {
                "can_adapt": True,
                "variant": schemas.RecipeVariantOut.model_validate(existing),
                "alternatives": [],
            }

    if user_for_update.transformations_limit != -1 and (
        user_for_update.transformations_used >= user_for_update.transformations_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You have reached the free recipes limit. Contact the administrator.",
        )

    user_for_update.transformations_used += 1
    db.commit()

    custom_instruction = (
        _sanitize_text(payload.custom_instruction, max_len=1000)
        if payload.custom_instruction is not None
        else None
    )

    try:
        if len(types) > 1:
            # Chain adaptations: apply each diet in order
            current = recipe
            for t in types:
                result = adapt_recipe(current, t, custom_instruction=None)
                if not result.get("can_adapt"):
                    return {
                        "can_adapt": False,
                        "variant": None,
                        "alternatives": result.get("alternatives", []),
                    }
                current = {
                    "title_pl": result["title_pl"],
                    "ingredients_pl": result["ingredients_pl"],
                    "steps_pl": result["steps_pl"],
                    "notes": result.get("notes", {}),
                }
            result = current
            variant_type = composite_key
            title_pl = result["title_pl"]
        else:
            single_type = types[0]
            result = adapt_recipe(recipe, single_type, custom_instruction)
            if not result.get("can_adapt"):
                return {
                    "can_adapt": False,
                    "variant": None,
                    "alternatives": result.get("alternatives", []),
                }
            if payload.custom_instruction:
                existing_count = (
                    db.query(models.RecipeVariant)
                    .filter(
                        models.RecipeVariant.recipe_id == recipe_id,
                        models.RecipeVariant.variant_type.like(f"{single_type}_alt%"),
                    )
                    .count()
                )
                variant_type = f"{single_type}_alt{existing_count}"
            else:
                variant_type = single_type
            title_pl = payload.custom_title or result["title_pl"]
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Adaptation failed: {e}")

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


@router.delete("/{recipe_id}/variants", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(
    recipe_id: int,
    payload: schemas.DeleteVariantRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    variant = (
        db.query(models.RecipeVariant)
        .filter_by(recipe_id=recipe_id, variant_type=payload.variant_type)
        .first()
    )
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    db.delete(variant)
    db.commit()


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
