import ipaddress
import re
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user, get_current_user_optional, get_optional_user_and_trial
from ..database import get_db
from ..quota import MAX_TRIAL_ACTIONS, enforce_trial_or_user_quota
from ..services.adaptation import adapt_recipe
from .recipes_helpers import (
    COMMON_PANTRY,
    get_recipe_or_404,
    ingredient_matches_user,
    normalize_adapt_types,
    normalize_ingredient_line,
    recipe_ingredient_lines,
    recipes_for_user_or_trial,
    user_ingredients_set,
    what_can_i_make_my_recipes,
)
from ..services.ingredient_alternatives import get_ingredient_alternatives
from ..services.recipe_image import save_user_upload
from ..services.translation import split_page_into_recipes, translate_recipe
from ..services.what_can_i_make_ai import suggest_recipe_from_ingredients, suggest_recipes_from_preferences

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

# Users with this email get unlimited transformations (no quota check, no increment).
_UNLIMITED_QUOTA_EMAIL = "tshprung@gmail.com"

def _has_unlimited_quota(user: models.User) -> bool:
    return (user.email or "").strip().lower() == _UNLIMITED_QUOTA_EMAIL

_TAG_RE = re.compile(r"<[^>]+>")
_MAX_FETCH_BYTES = 1_000 * 1024  # 1 MB
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
    # Some sites protect content with bot-block pages; try to detect those and
    # return a clearer error so users know to paste the recipe manually.
    lower = text.lower()
    if "made us think that you are a bot" in lower or "block page" in lower:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This website is blocking automated access. Please copy and paste the recipe text instead of using the URL.",
        )
    if len(text) < _MIN_EXTRACTED_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract recipe text from the provided URL.",
        )
    return text


def _create_recipes_from_chunks(
    chunks: list[str],
    source_url: str,
    payload: schemas.RecipeCreate,
    db: Session,
    current_user: models.User | None,
    trial_session,
):
    """Translate and create one recipe per chunk; return RecipeCreateMultiOut."""
    if current_user is not None:
        user_for_update = (
            db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
        )
    if current_user is not None:
        target_language = current_user.target_language
        target_country = current_user.target_country
        target_city = current_user.target_city
    else:
        target_language = (payload.target_language or trial_session.language)
        target_country = payload.target_country or trial_session.country
        target_city = ""

    created: list[models.Recipe] = []
    for raw_input in chunks:
        try:
            translated = translate_recipe(
                raw_input=raw_input,
                target_language=target_language,
                target_country=target_country,
                target_city=target_city,
            )
        except ValueError as e:
            if str(e).startswith("NOT_A_RECIPE:"):
                continue
            raise
        except Exception:
            raise
        notes = translated.get("notes", {}) or {}
        notes.setdefault("source_url", source_url)
        recipe = models.Recipe(
            user_id=current_user.id if current_user is not None else None,
            trial_session_id=trial_session.id if trial_session is not None else None,
            title_pl=translated.get("title_pl", "Untitled"),
            title_original=translated.get("title_original", (raw_input or "")[:100]),
            prep_time_minutes=translated.get("prep_time_minutes"),
            cook_time_minutes=translated.get("cook_time_minutes"),
            ingredients_pl=translated.get("ingredients_pl", []),
            ingredients_original=translated.get("ingredients_original", []),
            steps_pl=translated.get("steps_pl", []),
            tags=translated.get("tags", []),
            substitutions=translated.get("substitutions", {}),
            notes=notes,
            raw_input=raw_input,
            detected_language=translated.get("detected_language"),
            target_language=target_language,
            target_country=target_country,
            target_city=target_city,
        )
        if current_user is not None and not _has_unlimited_quota(current_user):
            user_for_update.transformations_used += 1
        db.add(recipe)
        created.append(recipe)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "This doesn't look like a recipe. Please paste the ingredients + steps, or try a different URL."
            ),
        )
    db.commit()
    for r in created:
        db.refresh(r)
    remaining = None
    if trial_session is not None:
        remaining = MAX_TRIAL_ACTIONS - trial_session.used_actions
    return schemas.RecipeCreateMultiOut(
        recipes=[schemas.RecipeOut.model_validate(r) for r in created],
        remaining_actions=remaining,
    )


@router.post(
    "/",
    response_model=schemas.RecipeOut | schemas.RecipeCreateTrialResponse | schemas.RecipeCreateMultiOut,
    status_code=status.HTTP_201_CREATED,
)
def create_recipe(
    payload: schemas.RecipeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    trial_session = enforce_trial_or_user_quota(request, db, current_user)
    if current_user is not None and not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )

    source_url = (payload.source_url or "").strip()
    if source_url:
        page_text = _fetch_and_extract_text(source_url)
        chunks = split_page_into_recipes(page_text)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "This doesn't look like a recipe. Please paste the ingredients + steps, or try a different URL. "
                    "If you think this is a mistake, contact tshprung.us@gmail.com."
                ),
            )
        # Multiple recipes from one URL: translate and create each
        if len(chunks) > 1:
            return _create_recipes_from_chunks(
                chunks=chunks,
                source_url=source_url,
                payload=payload,
                db=db,
                current_user=current_user,
                trial_session=trial_session,
            )
        raw_input = chunks[0]
    else:
        raw_input = _sanitize_text(payload.raw_input or "", max_len=10000)

    if current_user is not None:
        user_for_update = (
            db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
        )

    try:
        if current_user is not None:
            target_language = current_user.target_language
            target_country = current_user.target_country
            target_city = current_user.target_city
        else:
            target_language = (payload.target_language or trial_session.language)
            target_country = payload.target_country or trial_session.country
            target_city = ""
        translated = translate_recipe(
            raw_input=raw_input,
            target_language=target_language,
            target_country=target_country,
            target_city=target_city,
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

    notes = translated.get("notes", {}) or {}
    if source_url:
        notes.setdefault("source_url", source_url)

    recipe = models.Recipe(
        user_id=current_user.id if current_user is not None else None,
        trial_session_id=trial_session.id if trial_session is not None else None,
        title_pl=translated.get("title_pl", "Untitled"),
        title_original=translated.get("title_original", (raw_input or "")[:100]),
        prep_time_minutes=translated.get("prep_time_minutes"),
        cook_time_minutes=translated.get("cook_time_minutes"),
        ingredients_pl=translated.get("ingredients_pl", []),
        ingredients_original=translated.get("ingredients_original", []),
        steps_pl=translated.get("steps_pl", []),
        tags=translated.get("tags", []),
        substitutions=translated.get("substitutions", {}),
        notes=notes,
        raw_input=raw_input,
        detected_language=translated.get("detected_language"),
        target_language=target_language,
        target_country=target_country,
        target_city=target_city,
    )

    if current_user is not None and not _has_unlimited_quota(current_user):
        user_for_update.transformations_used += 1

    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    if trial_session is not None:
        return schemas.RecipeCreateTrialResponse(
            recipe=schemas.RecipeOut.model_validate(recipe),
            remaining_actions=MAX_TRIAL_ACTIONS - trial_session.used_actions,
        )
    return recipe


@router.post("/from-ai-suggestion", response_model=schemas.RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe_from_ai_suggestion(
    payload: schemas.FromAISuggestionRequest,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    """Create a recipe from an AI suggestion (e.g. Discover). No translation, no extra quota consumed.

    - Logged-in users: recipe is saved on the user (requires verified email, like other recipe operations).
    - Trial sessions: recipe is saved on the anonymous trial session.
    """
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if current_user is not None and not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )
    title = (payload.title or "").strip() or "Untitled"
    ingredients = payload.ingredients or []
    steps = payload.steps or []
    raw_input = title + "\n\nIngredients:\n" + "\n".join(f"- {s}" for s in ingredients) + "\n\nSteps:\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
    recipe = models.Recipe(
        user_id=current_user.id if current_user is not None else None,
        trial_session_id=trial_session.id if trial_session is not None else None,
        title_pl=title,
        title_original=title,
        ingredients_pl=ingredients,
        ingredients_original=ingredients,
        steps_pl=steps,
        tags=[],
        substitutions={},
        notes={},
        raw_input=raw_input,
        detected_language=current_user.target_language,
        target_language=current_user.target_language,
        target_country=current_user.target_country,
        target_city=current_user.target_city,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("/", response_model=list[schemas.RecipeOut])
def list_recipes(
    collection: str | None = None,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    recipes = recipes_for_user_or_trial(db, current_user, trial_session)
    if collection and collection.strip():
        coll = collection.strip().lower()
        recipes = [r for r in recipes if (r.collections or []) and any((c or "").strip().lower() == coll for c in r.collections)]
    return recipes


@router.get("/collections", response_model=schemas.RecipeCollectionsListOut)
def list_collections(
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    """Return distinct collection/filter names from recipes plus user-created filter names."""
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    recipes = recipes_for_user_or_trial(db, current_user, trial_session)
    names: set[str] = set()
    for r in recipes:
        for c in (r.collections or []):
            if isinstance(c, str) and c.strip():
                names.add(c.strip())
    if current_user is not None and getattr(current_user, "filter_names", None):
        for name in current_user.filter_names or []:
            if isinstance(name, str) and name.strip():
                names.add(name.strip())
    return schemas.RecipeCollectionsListOut(collections=sorted(names))


@router.post("/collections", response_model=schemas.RecipeCollectionsListOut)
def create_collection(
    payload: schemas.RecipeCollectionCreate,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    """
    Create a new filter/collection name.

    - Logged-in users: name is added to user.filter_names and merged with names from recipes.
    - Trial sessions: name is returned for immediate use and will persist once assigned to at least one trial recipe.
    """
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filter name is required.")
    name_lower = name.lower()

    names: set[str] = set()

    if current_user is not None:
        user = db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
        existing = list(user.filter_names or [])
        if any((n or "").strip().lower() == name_lower for n in existing):
            names.update((n or "").strip() for n in existing if (n or "").strip())
        else:
            user.filter_names = existing + [name]
            db.commit()
            db.refresh(user)
            names.update((n or "").strip() for n in (user.filter_names or []) if (n or "").strip())
        recipes = recipes_for_user_or_trial(db, user, None)
    else:
        # Trial: rely on recipe collections + the new name in the response.
        recipes = recipes_for_user_or_trial(db, None, trial_session)

    for r in recipes:
        for c in (r.collections or []):
            if isinstance(c, str) and c.strip():
                names.add(c.strip())
    names.add(name)
    return schemas.RecipeCollectionsListOut(collections=sorted(names))


@router.post("/collections/remove", status_code=status.HTTP_204_NO_CONTENT)
def remove_collection(
    payload: schemas.RecipeCollectionRemove,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    """Delete a collection: remove it from all recipes and from filter_names (for logged-in users)."""
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Collection name is required.")
    name_lower = name.lower()

    # Remove from recipes (user or trial).
    recipes = recipes_for_user_or_trial(db, current_user, trial_session)
    for r in recipes:
        if r.collections:
            new_list = [c for c in r.collections if (c or "").strip().lower() != name_lower]
            if len(new_list) != len(r.collections):
                r.collections = new_list

    # For logged-in users, also remove from filter_names.
    if current_user is not None:
        user = db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
        if user.filter_names:
            user.filter_names = [n for n in user.filter_names if (n or "").strip().lower() != name_lower]

    db.commit()
    return None


@router.post(
    "/what-can-i-make",
    response_model=schemas.WhatCanIMakeMyRecipesOut | schemas.WhatCanIMakeAIOut,
)
def what_can_i_make(
    payload: schemas.WhatCanIMakeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    """Find recipes the user can make from their ingredients (my_recipes) or return AI suggestions (ai)."""
    trial_session = enforce_trial_or_user_quota(request, db, current_user)
    if payload.source == "ai":
        return _what_can_i_make_ai(payload, current_user, trial_session, db)
    recipes = recipes_for_user_or_trial(db, current_user, trial_session)
    matches_result = what_can_i_make_my_recipes(
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


@router.post("/discover", response_model=schemas.DiscoverOut)
def discover_recipes(
    payload: schemas.DiscoverRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    """Return up to 3 AI-suggested recipes based on preferences (dish type, diet, allergens, max time). Consumes quota."""
    trial_session = enforce_trial_or_user_quota(request, db, current_user)
    if current_user is not None and not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )
    if current_user is not None:
        user_for_update = (
            db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
        )
        # Persist discovery preferences on the user so we can prefill next time.
        user_for_update.dish_preferences = payload.dish_types or []
        user_for_update.diet_filters = payload.diet_filters or []
        if payload.allergens is not None:
          user_for_update.allergens = payload.allergens or []
        if payload.custom_avoid_text is not None:
          user_for_update.custom_allergens_text = schemas.sanitize_custom_allergens_text(payload.custom_avoid_text)
        if not _has_unlimited_quota(current_user):
            user_for_update.transformations_used += 1
        db.commit()
    if current_user is not None:
        target_lang = (current_user.target_language or "").strip() or "en"
    else:
        target_lang = (trial_session.language or "").strip() or "en"
    try:
        recipes = suggest_recipes_from_preferences(
            dish_types=payload.dish_types or None,
            diet_filters=payload.diet_filters or None,
            max_time_minutes=payload.max_time_minutes,
            target_language=target_lang,
            keywords=payload.keywords,
            ingredients_text=payload.ingredients_text,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    # Always return at most three best-matching recipes.
    recipes = recipes[:3] if recipes else []
    out = schemas.DiscoverOut(
        suggestions=[schemas.AISuggestedRecipeOut(
            title=r["title"],
            ingredients=r["ingredients"],
            steps=r["steps"],
            missing_ingredients=r.get("missing_ingredients"),
        ) for r in recipes],
    )
    if trial_session is not None:
        out.remaining_actions = MAX_TRIAL_ACTIONS - trial_session.used_actions
    return out


def _what_can_i_make_ai(
    payload: schemas.WhatCanIMakeRequest,
    current_user: models.User | None,
    trial_session: models.TrialSession | None,
    db: Session,
) -> schemas.WhatCanIMakeAIOut:
    """AI path: generate recipe suggestion from ingredients + diet. Quota already consumed by caller."""
    if current_user is not None and not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )
    if current_user is not None:
        user_for_update = (
            db.execute(select(models.User).where(models.User.id == current_user.id)).scalar_one()
        )
        if not _has_unlimited_quota(current_user):
            user_for_update.transformations_used += 1
        db.commit()

    if current_user is not None:
        target_lang = (current_user.target_language or "").strip() or "en"
        avoid_terms = []
        if current_user.custom_allergens_text:
            raw = current_user.custom_allergens_text
            parts = [p.strip() for p in raw.replace(";", ",").split(",")]
            avoid_terms = [p for p in parts if p]
        allergen_codes = current_user.allergens or None
    else:
        target_lang = (trial_session.language or "").strip() or "en"
        avoid_terms = []
        allergen_codes = None
    try:
        suggestion = suggest_recipe_from_ingredients(
            ingredients=payload.ingredients or [],
            diet_filters=payload.diet_filters or None,
            allergen_codes=allergen_codes,
            avoid_terms=avoid_terms or None,
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
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return get_recipe_or_404(recipe_id, current_user, trial_session, db)


@router.post("/{recipe_id}/ingredient-match", response_model=schemas.RecipeIngredientMatchOut)
def recipe_ingredient_match(
    recipe_id: int,
    payload: schemas.RecipeIngredientMatchRequest,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    """Given a recipe and a list of ingredients the user has, return have_count, need_count, and missing_ingredients."""
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    recipe = get_recipe_or_404(recipe_id, current_user, trial_session, db)
    lines = recipe_ingredient_lines(recipe)
    if not lines:
        return schemas.RecipeIngredientMatchOut(have_count=0, need_count=0, missing_ingredients=[])
    user_set = user_ingredients_set(payload.ingredients or [], payload.assume_pantry)
    missing = [line for line in lines if not ingredient_matches_user(line, user_set)]
    have_count = len(lines) - len(missing)
    return schemas.RecipeIngredientMatchOut(
        have_count=have_count,
        need_count=len(lines),
        missing_ingredients=missing,
    )


_MAX_IMAGE_UPLOAD_BYTES = 3 * 1024 * 1024  # 3 MB
_ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png"}


@router.post("/{recipe_id}/image-upload", response_model=schemas.RecipeOut)
def upload_recipe_image(
    recipe_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    """Upload a custom recipe image (replaces existing). Accepts JPEG or PNG, max 3 MB."""
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    recipe = get_recipe_or_404(recipe_id, current_user, trial_session, db)
    content_type = (file.content_type or "").strip().lower()
    if content_type not in _ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG or PNG images are allowed.",
        )
    content = file.file.read()
    if len(content) > _MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image must be 3 MB or smaller.",
        )
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    ext = "png" if content_type == "image/png" else "jpg"
    try:
        image_url = save_user_upload(recipe_id, content, ext)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image.",
        ) from e
    recipe.image_url = image_url
    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}/image", response_model=schemas.RecipeOut)
def remove_recipe_image(
    recipe_id: int,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    """Remove the recipe image (clears image_url)."""
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    recipe = get_recipe_or_404(recipe_id, current_user, trial_session, db)
    recipe.image_url = None
    db.commit()
    db.refresh(recipe)
    return recipe


@router.patch("/{recipe_id}/notes", response_model=schemas.RecipeOut)
def update_notes(
    recipe_id: int,
    payload: schemas.RecipeUserNotesUpdate,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    recipe = get_recipe_or_404(recipe_id, current_user, trial_session, db)
    recipe.user_notes = payload.user_notes
    db.commit()
    db.refresh(recipe)
    return recipe


@router.patch("/{recipe_id}/favorite", response_model=schemas.RecipeOut)
def toggle_favorite(
    recipe_id: int,
    payload: schemas.RecipeFavoriteUpdate,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    recipe = get_recipe_or_404(recipe_id, current_user, trial_session, db)
    recipe.is_favorite = payload.is_favorite
    db.commit()
    db.refresh(recipe)
    return recipe


@router.patch("/{recipe_id}/meta", response_model=schemas.RecipeOut)
def update_recipe_meta(
    recipe_id: int,
    payload: schemas.RecipeMetaUpdate,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    recipe = get_recipe_or_404(recipe_id, current_user, trial_session, db)

    updates = payload.model_dump(exclude_unset=True)
    if "rating" in updates:
        recipe.user_rating = updates["rating"]
    if "prep_time_minutes" in updates:
        recipe.prep_time_minutes = updates["prep_time_minutes"]
    if "cook_time_minutes" in updates:
        recipe.cook_time_minutes = updates["cook_time_minutes"]
    if "servings_override" in updates:
        recipe.servings_override = updates["servings_override"]

    db.commit()
    db.refresh(recipe)
    return recipe


@router.patch("/{recipe_id}/collections", response_model=schemas.RecipeOut)
def update_recipe_collections(
    recipe_id: int,
    payload: schemas.RecipeCollectionsUpdate,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    recipe = get_recipe_or_404(recipe_id, current_user, trial_session, db)
    recipe.collections = [str(c).strip() for c in (payload.collections or []) if str(c).strip()]
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("/{recipe_id}/variants", response_model=list[schemas.RecipeVariantOut])
def list_variants(
    recipe_id: int,
    db: Session = Depends(get_db),
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    recipe = get_recipe_or_404(recipe_id, current_user, trial_session, db)
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
    recipe.prep_time_minutes = translated.get("prep_time_minutes", recipe.prep_time_minutes)
    recipe.cook_time_minutes = translated.get("cook_time_minutes", recipe.cook_time_minutes)
    recipe.detected_language = translated.get("detected_language", recipe.detected_language)
    recipe.target_language = current_user.target_language
    recipe.target_country = current_user.target_country
    recipe.target_city = current_user.target_city

    if not _has_unlimited_quota(current_user):
        user_for_update.transformations_used += 1
    db.commit()
    db.refresh(recipe)
    return recipe


@router.post("/{recipe_id}/adapt")
def adapt_recipe_endpoint(
    recipe_id: int,
    payload: schemas.AdaptRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    trial_session = enforce_trial_or_user_quota(request, db, current_user)
    recipe = get_recipe_or_404(recipe_id, current_user, trial_session, db)

    if current_user is not None and not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )

    types = normalize_adapt_types(getattr(payload, "variant_types", None), getattr(payload, "variant_type", None))
    composite_key = ",".join(types)

    if current_user is not None:
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
            out = {
                "can_adapt": True,
                "variant": schemas.RecipeVariantOut.model_validate(existing),
                "alternatives": [],
            }
            if trial_session is not None:
                out["remaining_actions"] = MAX_TRIAL_ACTIONS - trial_session.used_actions
            return out

    if current_user is not None and not _has_unlimited_quota(current_user):
        user_for_update.transformations_used += 1
    db.commit()

    custom_instruction = (
        _sanitize_text(payload.custom_instruction, max_len=1000)
        if payload.custom_instruction is not None
        else None
    )

    if current_user is not None:
        target_lang = (current_user.target_language or "").strip() or "en"
        target_country = current_user.target_country
        avoid_terms = []
        if current_user.custom_allergens_text:
            raw = current_user.custom_allergens_text
            parts = [p.strip() for p in raw.replace(";", ",").split(",")]
            avoid_terms = [p for p in parts if p]
    else:
        # Trial: use request body if provided (from Settings saved in localStorage), else session defaults
        target_lang = (payload.target_language or trial_session.language or "").strip() or "en"
        target_country = payload.target_country or trial_session.country
        avoid_terms = []

    try:
        if len(types) > 1:
            # Chain adaptations: apply each diet in order
            current = recipe
            for t in types:
                result = adapt_recipe(
                    current, t, custom_instruction=None, target_language=target_lang,
                    target_country=target_country,
                    avoid_terms=avoid_terms or None,
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
                recipe, single_type, custom_instruction, target_language=target_lang,
                target_country=target_country,
                avoid_terms=avoid_terms or None,
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
    out = {
        "can_adapt": True,
        "variant": schemas.RecipeVariantOut.model_validate(variant),
        "alternatives": [],
    }
    if trial_session is not None:
        out["remaining_actions"] = MAX_TRIAL_ACTIONS - trial_session.used_actions
    return out


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
            detail="Insufficient credits. Ingredient alternatives use one credit. Contact the administrator or upgrade.",
        )

    target_lang = (current_user.target_language or "").strip() or "en"
    try:
        alternatives = get_ingredient_alternatives(
            ingredient=payload.ingredient,
            diet_filters=payload.diet_filters or None,
            target_language=target_lang,
            target_country=current_user.target_country,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    if not _has_unlimited_quota(current_user):
        user_for_update.transformations_used += 1
    db.commit()

    return schemas.IngredientAlternativesOut(
        alternatives=[schemas.IngredientAlternativeOut(name=a["name"], notes=a.get("notes")) for a in alternatives],
    )


@router.post("/{recipe_id}/replace-ingredient", response_model=schemas.RecipeOut | schemas.RecipeVariantOut)
def replace_ingredient(
    recipe_id: int,
    payload: schemas.ReplaceIngredientRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Replace an ingredient line in the original recipe or a variant."""
    recipe = db.get(models.Recipe, recipe_id)
    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    idx = payload.ingredient_index
    new_line = (payload.new_ingredient or "").strip()
    if not new_line:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="New ingredient cannot be empty")

    if payload.variant_type:
        variant = (
            db.query(models.RecipeVariant)
            .filter_by(recipe_id=recipe_id, variant_type=payload.variant_type)
            .first()
        )
        if not variant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
        if idx >= len(variant.ingredients_pl or []):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Ingredient index out of range")
        ingredients = list(variant.ingredients_pl or [])
        ingredients[idx] = new_line
        variant.ingredients_pl = ingredients
        db.commit()
        db.refresh(variant)
        return schemas.RecipeVariantOut.model_validate(variant)

    # Original recipe
    if idx >= len(recipe.ingredients_pl or []):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Ingredient index out of range")
    ingredients = list(recipe.ingredients_pl or [])
    ingredients[idx] = new_line
    recipe.ingredients_pl = ingredients
    db.commit()
    db.refresh(recipe)
    return schemas.RecipeOut.model_validate(recipe)


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
    user_and_trial: tuple = Depends(get_optional_user_and_trial),
):
    current_user, trial_session = user_and_trial
    if current_user is None and trial_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    recipe = get_recipe_or_404(recipe_id, current_user, trial_session, db)
    # Remove from any shopping lists before deleting the recipe
    db.query(models.ShoppingListRecipe).filter(
        models.ShoppingListRecipe.recipe_id == recipe_id
    ).delete()
    db.delete(recipe)
    if current_user is not None:
        db.query(models.ShoppingListCache).filter(
            models.ShoppingListCache.user_id == current_user.id
        ).delete(synchronize_session=False)
    db.commit()
