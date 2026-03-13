"""Starter recipes for new users: 3 recipes from famous cooks per country (AI + fallback)."""
import json
import logging
import os

from openai import APIError, OpenAI, RateLimitError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You return exactly 3 classic recipes from well-known cooks or chefs of the given country.
Each recipe must have: title, ingredients (list of strings), steps (list of strings), author_name, author_bio.
author_bio is 1-2 sentences: why they are famous in that country (e.g. TV show host, cookbook author, restaurant chef).
Output valid JSON only — no markdown, no prose. Use the output_language for all text.
"""

USER_PROMPT_TEMPLATE = """\
Country: {country_name}
Output language: {output_lang}
{dish_types_line}{diet_constraint_line}

Return exactly this JSON (array of 3 recipes from famous cooks in that country):
{{
  "recipes": [
    {{
      "title": "<recipe title in {output_lang}>",
      "ingredients": ["<ingredient 1>", "<ingredient 2>", ...],
      "steps": ["<step 1>", "<step 2>", ...],
      "author_name": "<full name of a real famous cook/chef from this country>",
      "author_bio": "<1-2 sentences: e.g. TV show host, cookbook author, Michelin chef>",
      "tags": ["<tag1 in {output_lang}>", "<tag2>", ...]
    }},
    ... (3 recipes total, each from a different well-known figure)
  ]
}}

For each recipe, include 2-4 short tags in {output_lang} (e.g. breakfast, lunch, dinner, dessert, easy, quick, traditional, vegetarian, soup, main course — whatever fits the recipe).
"""

_LANG_NAMES = {
    "en": "English",
    "pl": "Polish",
    "he": "Hebrew",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "uk": "Ukrainian",
    "nl": "Dutch",
    "tr": "Turkish",
    "ja": "Japanese",
    "zh": "Chinese",
}

_COUNTRY_NAMES = {
    "PL": "Poland",
    "IL": "Israel",
    "US": "United States",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "ES": "Spain",
    "IT": "Italy",
}


def _output_lang_name(code: str) -> str:
    return _LANG_NAMES.get((code or "").strip().lower(), "English")


def _country_name(code: str) -> str:
    return _COUNTRY_NAMES.get((code or "").strip().upper(), code or "the country")


def _fallback_recipes(target_language: str) -> list[dict]:
    """Return 3 simple fallback recipes when AI is unavailable. Minimal author info."""
    lang = (target_language or "en").strip().lower()
    if lang == "pl":
        return [
            {
                "title": "Zupa pomidorowa",
                "ingredients": ["pomidory", "cebula", "czosnek", "bulion", "bazylia", "sól", "pieprz"],
                "steps": ["Ugotuj pomidory z cebulą i czosnkiem.", "Zmiksuj, dopraw solą i pieprzem.", "Podawaj z bazylią."],
                "author_name": "Kuchnia domowa",
                "author_bio": "Klasyczna polska kuchnia.",
                "author_image_url": None,
                "tags": ["zupa", "łatwe", "obiad"],
            },
            {
                "title": "Kotlet schabowy",
                "ingredients": ["schab", "jajko", "bułka tarta", "sól", "olej"],
                "steps": ["Rozbij mięso.", "Panieruj w jajku i bułce tartej.", "Usmaż na oleju na złoto."],
                "author_name": "Kuchnia domowa",
                "author_bio": "Tradycyjna polska potrawa.",
                "author_image_url": None,
                "tags": ["danie główne", "tradycyjne", "mięso"],
            },
            {
                "title": "Sałatka jarzynowa",
                "ingredients": ["ziemniaki", "marchew", "groszek", "ogórek kiszony", "majonez", "sól"],
                "steps": ["Ugotuj warzywa, ostudź.", "Pokrój w kostkę, wymieszaj z majonezem.", "Dopraw solą."],
                "author_name": "Kuchnia domowa",
                "author_bio": "Prosta sałatka na każdy dzień.",
                "author_image_url": None,
                "tags": ["sałatka", "łatwe", "na zimno"],
            },
        ]
    # Default English fallback
    return [
        {
            "title": "Tomato soup",
            "ingredients": ["tomatoes", "onion", "garlic", "stock", "basil", "salt", "pepper"],
            "steps": ["Cook tomatoes with onion and garlic.", "Blend, season with salt and pepper.", "Serve with basil."],
            "author_name": "Home cooking",
            "author_bio": "Classic simple recipe.",
            "author_image_url": None,
            "tags": ["soup", "easy", "lunch"],
        },
        {
            "title": "Grilled chicken",
            "ingredients": ["chicken breast", "olive oil", "lemon", "herbs", "salt", "pepper"],
            "steps": ["Coat chicken with oil and herbs.", "Grill until cooked through.", "Serve with lemon."],
            "author_name": "Home cooking",
            "author_bio": "Quick and healthy.",
            "author_image_url": None,
            "tags": ["main course", "easy", "quick"],
        },
        {
            "title": "Green salad",
            "ingredients": ["lettuce", "cucumber", "tomato", "olive oil", "vinegar", "salt"],
            "steps": ["Wash and chop vegetables.", "Toss with oil and vinegar.", "Season with salt."],
            "author_name": "Home cooking",
            "author_bio": "Fresh and easy.",
            "author_image_url": None,
            "tags": ["salad", "easy", "side"],
        },
    ]


def get_starter_recipes(
    target_country: str,
    target_language: str,
    dish_preferences: list[str] | None = None,
    diet_filters: list[str] | None = None,
) -> list[dict]:
    """
    Return 3 starter recipes for the given country and language.
    Optionally prefer recipe types matching dish_preferences (e.g. ["pasta", "soups"]).
    If diet_filters (e.g. ["kosher", "vegetarian"]) are set, all recipes MUST comply with those diets
    (either choose compliant recipes or adapt ingredients/steps so the recipe is compliant).
    Each dict has: title, ingredients (list), steps (list), author_name, author_bio, author_image_url (optional), tags (list of short strings, e.g. breakfast, easy, dessert).
    Uses OpenAI when available; falls back to static recipes on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.info("OPENAI_API_KEY not set; using fallback starter recipes")
        return _fallback_recipes(target_language)

    country_name = _country_name(target_country)
    output_lang = _output_lang_name(target_language)
    dish_types_line = ""
    if dish_preferences:
        types_str = ", ".join(dish_preferences[:10])  # limit for prompt
        dish_types_line = f"Prefer recipes that match these types (if possible): {types_str}.\n"
    diet_constraint_line = ""
    if diet_filters:
        diets_str = ", ".join(diet_filters[:8])
        diet_constraint_line = (
            f"CRITICAL: The user's diet requirements are: {diets_str}. "
            "Every recipe MUST be compliant with these diets: either choose recipes that already comply, "
            "or adapt ingredients and steps so the recipe is fully compliant (e.g. for kosher: no pork, "
            "no mixing meat and dairy; for vegetarian/vegan: no meat/fish). No exceptions.\n"
        )
    prompt = USER_PROMPT_TEMPLATE.format(
        country_name=country_name,
        output_lang=output_lang,
        dish_types_line=dish_types_line,
        diet_constraint_line=diet_constraint_line,
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=2048,
            temperature=0.5,
        )
    except (RateLimitError, APIError) as e:
        logger.warning("Starter recipes OpenAI error: %s; using fallback", e)
        return _fallback_recipes(target_language)

    content = response.choices[0].message.content
    if not content:
        return _fallback_recipes(target_language)
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return _fallback_recipes(target_language)

    recipes = data.get("recipes") or []
    out = []
    for r in recipes[:3]:
        if not isinstance(r, dict):
            continue
        title = str(r.get("title") or "").strip() or "Recipe"
        ingredients = [str(x).strip() for x in r.get("ingredients", []) if x]
        steps = [str(x).strip() for x in r.get("steps", []) if x]
        author_name = (str(r.get("author_name") or "").strip()) or None
        author_bio = (str(r.get("author_bio") or "").strip()) or None
        author_image_url = (str(r.get("author_image_url") or "").strip()) or None
        tags = [str(x).strip() for x in r.get("tags", []) if x and str(x).strip()][:10]
        out.append({
            "title": title,
            "ingredients": ingredients,
            "steps": steps,
            "author_name": author_name,
            "author_bio": author_bio,
            "author_image_url": author_image_url,
            "tags": tags,
        })
    if len(out) < 3:
        # Pad with fallback if AI returned fewer than 3
        fallback = _fallback_recipes(target_language)
        for i in range(3 - len(out)):
            out.append(fallback[i])
    return out[:3]


def ensure_starter_recipes_for_user(user, db) -> None:
    """
    If this user has 0 recipes and has not yet received starter recipes, create 3 and set starter_recipes_added.
    Does not consume credits. Idempotent: only runs once per user.
    """
    from .. import models

    if user.starter_recipes_added:
        return
    count = db.query(models.Recipe).filter(models.Recipe.user_id == user.id).count()
    if count > 0:
        return
    recipes_data = get_starter_recipes(
        user.target_country,
        user.target_language,
        dish_preferences=user.dish_preferences or None,
        diet_filters=user.diet_filters or None,
    )
    add_starter_recipes_to_user(user, recipes_data, db, diet_filters=user.diet_filters or None)


def add_starter_recipes_to_user(
    user, recipes_data: list[dict], db, diet_filters: list[str] | None = None
) -> None:
    """
    Create Recipe rows from recipes_data and attach to user; set starter_recipes_added=True.
    If diet_filters is set (e.g. ["kosher"]), set recipe.diet_tags so the UI can show a diet badge.
    Used by ensure_starter_recipes_for_user and by onboarding claim.
    """
    from .. import models
    from .recipe_image import get_or_create_recipe_image

    diet_tags = list(diet_filters) if diet_filters else []
    created: list[models.Recipe] = []
    for r in recipes_data:
        title = (r.get("title") or "").strip() or "Recipe"
        ingredients = r.get("ingredients") or []
        steps = r.get("steps") or []
        raw_input = (
            title
            + "\n\nIngredients:\n"
            + "\n".join(f"- {s}" for s in ingredients)
            + "\n\nSteps:\n"
            + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
        )
        tags_list = [str(x).strip() for x in r.get("tags", []) if x and str(x).strip()][:10]
        recipe = models.Recipe(
            user_id=user.id,
            title_pl=title,
            title_original=title,
            ingredients_pl=ingredients,
            ingredients_original=ingredients,
            steps_pl=steps,
            tags=tags_list,
            substitutions={},
            notes={},
            raw_input=raw_input,
            detected_language=user.target_language,
            target_language=user.target_language,
            target_country=user.target_country,
            target_city=user.target_city,
            author_name=(r.get("author_name") or "").strip() or None,
            author_bio=(r.get("author_bio") or "").strip() or None,
            author_image_url=(r.get("author_image_url") or "").strip() or None,
            diet_tags=diet_tags,
        )
        db.add(recipe)
        created.append(recipe)
    user.starter_recipes_added = True
    db.commit()
    for recipe in created:
        try:
            get_or_create_recipe_image(recipe, db)
        except Exception:
            pass


def add_starter_recipes_to_trial_session(trial_session, recipes_data: list[dict], db) -> list:
    """
    Create Recipe rows for a trial session (no user_id). Generate dish images.
    Returns list of created Recipe models.
    """
    from .. import models
    from .recipe_image import get_or_create_recipe_image

    created: list[models.Recipe] = []
    for r in recipes_data:
        title = (r.get("title") or "").strip() or "Recipe"
        ingredients = r.get("ingredients") or []
        steps = r.get("steps") or []
        raw_input = (
            title
            + "\n\nIngredients:\n"
            + "\n".join(f"- {s}" for s in ingredients)
            + "\n\nSteps:\n"
            + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
        )
        tags_list = [str(x).strip() for x in r.get("tags", []) if x and str(x).strip()][:10]
        recipe = models.Recipe(
            user_id=None,
            trial_session_id=trial_session.id,
            title_pl=title,
            title_original=title,
            ingredients_pl=ingredients,
            ingredients_original=ingredients,
            steps_pl=steps,
            tags=tags_list,
            substitutions={},
            notes={},
            raw_input=raw_input,
            detected_language=trial_session.language,
            target_language=trial_session.language or "en",
            target_country=trial_session.country or "PL",
            target_city="",
            author_name=(r.get("author_name") or "").strip() or None,
            author_bio=(r.get("author_bio") or "").strip() or None,
            author_image_url=(r.get("author_image_url") or "").strip() or None,
            diet_tags=tags_list,
        )
        db.add(recipe)
        created.append(recipe)
    db.commit()
    for recipe in created:
        try:
            get_or_create_recipe_image(recipe, db)
        except Exception:
            pass
    db.commit()
    return created
