"""
Recipe dish image: cache-first lookup by normalized title (and optional language),
then on miss generate via OpenAI Images API and save to static storage.
"""

import base64
import logging
import os
import re
import unicodedata

from openai import APIError, OpenAI, RateLimitError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger(__name__)

# Directory for saved images; served at /static/recipe-images/
_BASE_DIR = os.getenv(
    "RECIPE_IMAGES_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "static", "recipe-images"),
)
# URL path prefix stored in DB (no leading host)
STATIC_URL_PREFIX = "/static/recipe-images"


def get_storage_dir() -> str:
    """Return the directory path for recipe images (for user uploads)."""
    _ensure_storage_dir()
    return _BASE_DIR


def save_user_upload(recipe_id: int, content: bytes, extension: str) -> str:
    """
    Save user-uploaded image to disk. Returns the URL path to store on the recipe.
    Does not update cache. extension should be e.g. 'jpg' or 'png'.
    """
    _ensure_storage_dir()
    ext = (extension or "jpg").lower().lstrip(".")
    if ext not in ("jpg", "jpeg", "png"):
        ext = "jpg"
    filename = f"{recipe_id}-user.{ext}"
    filepath = os.path.join(_BASE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return f"{STATIC_URL_PREFIX}/{filename}"


def _normalize_cache_key(title: str, target_language: str | None = None) -> str:
    """Normalize recipe title to a stable cache key: lowercase, collapse spaces, alphanumeric + underscore."""
    if not title or not isinstance(title, str):
        return "untitled"
    # Normalize unicode (e.g. NFD -> NFC), lowercase, replace non-alphanumeric with space
    s = unicodedata.normalize("NFKC", title.strip().lower())
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    s = re.sub(r"\s+", "_", s).strip("_") or "untitled"
    # Optional: append language so same dish in different locales can share or differ
    if target_language:
        s = f"{s}_{target_language}"
    return s[:200]  # cap length


def _ensure_storage_dir() -> None:
    os.makedirs(_BASE_DIR, exist_ok=True)


def _generate_image_via_openai(prompt: str) -> bytes | None:
    """Call OpenAI Images API (DALL-E 2), return image bytes or None on failure."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; skipping recipe image generation")
        return None
    try:
        client = OpenAI(api_key=api_key)
        resp = client.images.generate(
            model="dall-e-2",
            prompt=prompt[:1000],
            n=1,
            size="512x512",
            response_format="b64_json",
        )
        if not resp.data or len(resp.data) == 0:
            return None
        return base64.b64decode(resp.data[0].b64_json)
    except (APIError, RateLimitError) as e:
        logger.warning("OpenAI Images API error: %s", e)
        return None
    except Exception as e:
        logger.exception("Recipe image generation failed: %s", e)
        return None


def get_or_create_recipe_image(
    recipe: models.Recipe,
    db: Session,
) -> None:
    """
    Ensure recipe has an image_url: check cache by normalized title (+ language);
    if cache hit, set recipe.image_url and return. On miss, generate image, save to disk,
    insert cache row, set recipe.image_url. Commits at the end.
    """
    if recipe.image_url:
        return
    cache_key = _normalize_cache_key(recipe.title_pl or recipe.title_original, recipe.target_language)
    # Cache lookup
    cached = db.execute(
        select(models.RecipeImageCache).where(models.RecipeImageCache.cache_key == cache_key)
    ).scalars().first()
    if cached:
        recipe.image_url = cached.image_url
        db.commit()
        return
    # Cache miss: generate and save
    title = recipe.title_pl or recipe.title_original or "Dish"
    prompt = (
        f"Realistic food photo of {title}, plated dish only, natural lighting, close-up, "
        "high quality, no people, no hands, no text, no logos."
    )
    image_bytes = _generate_image_via_openai(prompt)
    if not image_bytes:
        return
    _ensure_storage_dir()
    filename = f"{recipe.id}.jpg"
    filepath = os.path.join(_BASE_DIR, filename)
    try:
        with open(filepath, "wb") as f:
            f.write(image_bytes)
    except OSError as e:
        logger.warning("Could not save recipe image to %s: %s", filepath, e)
        return
    image_url = f"{STATIC_URL_PREFIX}/{filename}"
    cache_row = models.RecipeImageCache(cache_key=cache_key, image_url=image_url)
    db.add(cache_row)
    recipe.image_url = image_url
    db.commit()
