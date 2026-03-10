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
from ..services.ingredient_alternatives import get_ingredient_alternatives
from ..services.translation import translate_recipe
from ..services.what_can_i_make_ai import suggest_recipe_from_ingredients

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

# Users with this email get unlimited transformations (no quota check, no increment).
_UNLIMITED_QUOTA_EMAIL = "tshprung@gmail.com"

def _has_unlimited_quota(user: models.User) -> bool:
    return (user.email or "").strip().lower() == _UNLIMITED_QUOTA_EMAIL

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
    if not _has_unlimited_quota(current_user) and user_for_update.transformations_limit != -1 and (
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

    # Consume quota only for valid recipe creation (unless unlimited)
    if not _has_unlimited_quota(current_user):
        user_for_update.transformations_used += 1

    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def _recipe_matches_query(recipe: models.Recipe, q: str) -> bool:
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


@router.get("/", response_model=list[schemas.RecipeOut])
def list_recipes(
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipes = db.query(models.Recipe).filter(models.Recipe.user_id == current_user.id).all()
    if q and q.strip():
        recipes = [r for r in recipes if _recipe_matches_query(r, q)]
    return recipes


# Common pantry items assumed if assume_pantry is True (lowercase for matching)
_COMMON_PANTRY = {
    "salt", "sugar", "pepper", "black pepper", "oil", "olive oil", "vegetable oil",
    "water", "flour", "vanilla", "vinegar", "baking powder", "baking soda",
    "soy sauce", "paprika", "cumin", "oregano", "basil", "garlic", "onion",
    "butter", "milk", "eggs", "honey", "mustard", "ketchup",
}


def _normalize_ingredient_line(item) -> str:
    """Extract a single line of text from an ingredient (string or dict)."""
    if isinstance(item, str):
        return (item or "").strip()
    if isinstance(item, dict):
        return f"{item.get('amount', '')} {item.get('name', '')}".strip()
    return str(item).strip()


def _recipe_ingredient_lines(recipe: models.Recipe) -> list[str]:
    """List of normalized ingredient lines for a recipe (from ingredients_pl)."""
    lines = []
    for item in recipe.ingredients_pl or []:
        line = _normalize_ingredient_line(item)
        if line:
            lines.append(line.lower())
    return lines


def _user_ingredients_set(ingredients: list[str], assume_pantry: bool) -> set[str]:
    """Set of normalized user ingredient strings (plus pantry if assumed)."""
    out = set()
    for s in ingredients or []:
        t = (s or "").strip().lower()
        if t:
            out.add(t)
    if assume_pantry:
        out |= _COMMON_PANTRY
    return out


def _ingredient_matches_user(recipe_line: str, user_set: set[str]) -> bool:
    """True if recipe_line is 'covered' by any user ingredient (substring or exact)."""
    recipe_lower = recipe_line.lower()
    for u in user_set:
        if u in recipe_lower or recipe_lower in u:
            return True
    # Also check individual words (e.g. user has "lemon", recipe has "2 lemons juice")
    for word in recipe_lower.replace(",", " ").split():
        word = word.strip()
        if len(word) < 3:
            continue
        for u in user_set:
            if word in u or u in word:
                return True
    return False


def _recipe_meat_dairy_keywords(recipe: models.Recipe) -> tuple[bool, bool]:
    """Returns (has_meat, has_dairy) based on ingredient text."""
    text = " ".join(_recipe_ingredient_lines(recipe)).lower()
    meat = any(w in text for w in (
        "meat", "chicken", "beef", "pork", "lamb", "fish", "salmon", "tuna",
        "mięso", "kurczak", "wołowina", "wieprzowina", "ryba", "łosoś",
    ))
    dairy = any(w in text for w in (
        "milk", "cream", "cheese", "butter", "yogurt",
        "mleko", "śmietana", "ser", "masło", "jogurt",
    ))
    return meat, dairy


def _what_can_i_make_my_recipes(
    recipes: list[models.Recipe],
    user_ingredients: list[str],
    assume_pantry: bool,
    diet_filters: list[str] | None,
) -> list[tuple[models.Recipe, bool, list[str]]]:
    """Returns list of (recipe, can_make, missing_ingredients) sorted by best match."""
    user_set = _user_ingredients_set(user_ingredients, assume_pantry)
    results = []
    for recipe in recipes:
        lines = _recipe_ingredient_lines(recipe)
        if not lines:
            continue
        # Diet filter: if user wants vegetarian/vegan, exclude meat-based; if dairy_free, exclude dairy
        if diet_filters:
            meat, dairy = _recipe_meat_dairy_keywords(recipe)
            if "vegetarian" in diet_filters or "vegan" in diet_filters:
                if meat:
                    continue
            if "dairy_free" in diet_filters and dairy:
                continue
        missing = []
        for line in lines:
            if not _ingredient_matches_user(line, user_set):
                missing.append(line)
        can_make = len(missing) == 0
        results.append((recipe, can_make, missing))
    # Sort: can_make first, then by fewest missing, then by most ingredients matched
    results.sort(key=lambda x: (not x[1], len(x[2]), -len(_recipe_ingredient_lines(x[0]))))
    return results


@router.post(
    "/what-can-i-make",
    response_model=schemas.WhatCanIMakeMyRecipesOut | schemas.WhatCanIMakeAIOut,
)
def what_can_i_make(
    payload: schemas.WhatCanIMakeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Find recipes the user can make from their ingredients (my_recipes) or return AI suggestions (ai)."""
    if payload.source == "ai":
        return _what_can_i_make_ai(payload, current_user, db)
    recipes = (
        db.query(models.Recipe)
        .filter(models.Recipe.user_id == current_user.id)
        .all()
    )
    matches_result = _what_can_i_make_my_recipes(
        recipes,
        payload.ingredients or [],
        payload.assume_pantry,
        payload.diet_filters or [],
    )
    matches = [
        schemas.WhatCanIMakeMatchOut(
            recipe=schemas.RecipeOut.model_validate(r),
            can_make=can_make,
            missing_ingredients=missing,
        )
        for r, can_make, missing in matches_result
    ]
    return schemas.WhatCanIMakeMyRecipesOut(source="my_recipes", matches=matches)


def _what_can_i_make_ai(
    payload: schemas.WhatCanIMakeRequest,
    current_user: models.User,
    db: Session,
) -> schemas.WhatCanIMakeAIOut:
    """AI path: generate recipe suggestion from ingredients + diet. Consumes 1 token."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )
    user_for_update = (
        db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
    )
    if not _has_unlimited_quota(current_user) and user_for_update.transformations_limit != -1 and (
        user_for_update.transformations_used >= user_for_update.transformations_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You have reached the free recipes limit. Contact the administrator.",
        )
    if not _has_unlimited_quota(current_user):
        user_for_update.transformations_used += 1
    db.commit()

    target_lang = (current_user.target_language or "").strip() or "en"
    try:
        suggestion = suggest_recipe_from_ingredients(
            ingredients=payload.ingredients or [],
            diet_filters=payload.diet_filters or None,
            assume_pantry=payload.assume_pantry,
            target_language=target_lang,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return schemas.WhatCanIMakeAIOut(
        source="ai",
        suggestions=[
            schemas.AISuggestedRecipeOut(
                title=suggestion["title"],
                ingredients=suggestion["ingredients"],
                steps=suggestion["steps"],
                missing_ingredients=suggestion.get("missing_ingredients") or None,
            )
        ],
    )


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


def _recipe_needs_relocalize(recipe: models.Recipe, user: models.User) -> bool:
    """True if recipe locale differs from user's current settings (so re-localize is meaningful)."""
    return (
        (recipe.target_language or "").strip() != (user.target_language or "").strip()
        or (recipe.target_country or "").strip() != (user.target_country or "").strip()
        or (recipe.target_city or "").strip() != (user.target_city or "").strip()
    )


@router.post("/{recipe_id}/relocalize", response_model=schemas.RecipeOut)
def relocalize_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    if not _recipe_needs_relocalize(recipe, current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe is already in your current language and location. Change settings first if you want a different localization.",
        )

    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )

    # Quota check before OpenAI cost, but do not consume quota yet
    user_for_update = (
        db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
    )
    if not _has_unlimited_quota(current_user) and user_for_update.transformations_limit != -1 and (
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

    if not _has_unlimited_quota(current_user):
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

    if not _has_unlimited_quota(current_user) and user_for_update.transformations_limit != -1 and (
        user_for_update.transformations_used >= user_for_update.transformations_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You have reached the free recipes limit. Contact the administrator.",
        )

    if not _has_unlimited_quota(current_user):
        user_for_update.transformations_used += 1
    db.commit()

    custom_instruction = (
        _sanitize_text(payload.custom_instruction, max_len=1000)
        if payload.custom_instruction is not None
        else None
    )

    target_lang = (current_user.target_language or "").strip() or "en"

    try:
        if len(types) > 1:
            # Chain adaptations: apply each diet in order
            current = recipe
            for t in types:
                result = adapt_recipe(
                    current, t, custom_instruction=None, target_language=target_lang
                )
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
            result = adapt_recipe(
                recipe, single_type, custom_instruction, target_language=target_lang
            )
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


@router.post(
    "/{recipe_id}/ingredient-alternatives",
    response_model=schemas.IngredientAlternativesOut,
)
def ingredient_alternatives(
    recipe_id: int,
    payload: schemas.IngredientAlternativesRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get alternative ingredients for a given ingredient, optionally filtered by diet. Consumes one transformation."""
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )

    user_for_update = (
        db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
    )
    if not _has_unlimited_quota(current_user) and user_for_update.transformations_limit != -1 and (
        user_for_update.transformations_used >= user_for_update.transformations_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You have reached the free recipes limit. Contact the administrator.",
        )

    if not _has_unlimited_quota(current_user):
        user_for_update.transformations_used += 1
    db.commit()

    target_lang = (current_user.target_language or "").strip() or "en"
    try:
        alternatives = get_ingredient_alternatives(
            ingredient=payload.ingredient,
            diet_filters=payload.diet_filters or None,
            target_language=target_lang,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return schemas.IngredientAlternativesOut(
        alternatives=[schemas.IngredientAlternativeOut(name=a["name"], notes=a.get("notes")) for a in alternatives],
    )


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
