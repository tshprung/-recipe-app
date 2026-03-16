"""AI suggestion for 'What can I make' — generate a recipe from ingredients + diet."""
import json
import os

from openai import APIError, OpenAI, RateLimitError

SYSTEM_PROMPT = """\
You suggest a single recipe that the user can make with the ingredients they have.
Respect their diet restrictions. Output valid JSON only — no markdown, no prose.
If they have basic pantry (salt, sugar, oil, etc.) assume those are available when assume_pantry is true.
Return one recipe with title, ingredients (list of strings), and steps (list of strings).
Optionally include "missing_ingredients": list of items they might need to buy if the recipe is close but not fully makeable.
CRITICAL: If the user provided allergens/avoid terms, do NOT include those ingredients. Prefer a different recipe over suggesting something unsafe.
"""

USER_PROMPT_TEMPLATE = """\
Ingredients the user has: {ingredients}

Diet restrictions: {diet_list}

Allergens to avoid (codes): {allergen_codes}
Other avoid terms (free text): {avoid_terms}

Assume basic pantry (salt, sugar, oil, pepper, etc.): {assume_pantry}

Output language: {output_lang}

Return exactly this JSON (one recipe they can make, or the closest option):
{{
  "title": "<recipe title in {output_lang}>",
  "ingredients": ["<ingredient 1>", "<ingredient 2>", ...],
  "steps": ["<step 1>", "<step 2>", ...],
  "missing_ingredients": ["<item not in their list if recipe is close>"] or []
}}
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


def _output_lang_name(code: str) -> str:
    return _LANG_NAMES.get((code or "").strip().lower(), "English")


def suggest_recipe_from_ingredients(
    ingredients: list[str],
    diet_filters: list[str] | None = None,
    allergen_codes: list[str] | None = None,
    avoid_terms: list[str] | None = None,
    assume_pantry: bool = True,
    target_language: str = "en",
) -> dict:
    """
    Return one suggested recipe: { title, ingredients, steps, missing_ingredients }.
    Raises RuntimeError on missing API key or rate limit.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")

    ingredients_str = ", ".join((s or "").strip() for s in (ingredients or []) if (s or "").strip())
    if not ingredients_str:
        ingredients_str = "none specified"
    diet_list = ", ".join(diet_filters) if diet_filters else "none"
    allergen_codes_str = ", ".join((s or "").strip() for s in (allergen_codes or []) if (s or "").strip()) or "none"
    avoid_terms_str = ", ".join((s or "").strip() for s in (avoid_terms or []) if (s or "").strip()) or "none"
    output_lang = _output_lang_name(target_language)

    prompt = USER_PROMPT_TEMPLATE.format(
        ingredients=ingredients_str,
        diet_list=diet_list,
        allergen_codes=allergen_codes_str,
        avoid_terms=avoid_terms_str,
        assume_pantry="yes" if assume_pantry else "no",
        output_lang=output_lang,
    )

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=1024,
            temperature=0.4,
        )
    except RateLimitError as e:
        raise RuntimeError("OpenAI rate limit exceeded, please try again later.") from e
    except APIError as e:
        msg = str(e)
        if "insufficient_quota" in msg or "exceeded your current quota" in msg:
            raise RuntimeError("OpenAI quota exceeded.") from e
        raise

    content = response.choices[0].message.content
    if not content:
        return {"title": "", "ingredients": [], "steps": [], "missing_ingredients": []}
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {"title": "", "ingredients": [], "steps": [], "missing_ingredients": []}
    return {
        "title": str(data.get("title", "")).strip(),
        "ingredients": [str(x).strip() for x in data.get("ingredients", []) if x],
        "steps": [str(x).strip() for x in data.get("steps", []) if x],
        "missing_ingredients": [str(x).strip() for x in data.get("missing_ingredients", []) if x],
    }


DISCOVER_SYSTEM_PROMPT = """\
You act as an internet-scale recipe search assistant.

Your job:
- Understand the user's theme/keywords (e.g. Passover charoset, Rosh Hashanah desserts, weekday pasta).
- Use that plus dish types, diets, max cooking time, and important ingredients to imagine 1–2 excellent recipes
  the user could realistically cook at home.

Rules:
- Output valid JSON only — no markdown, no prose outside the JSON.
- Each recipe must have: title, ingredients (list of strings), steps (list of strings).
- Respect diet restrictions and \"avoid\" terms as best you can.
- Keep recipes practical, clear, and easy to follow.
- If ingredients_text is provided, prefer recipes that meaningfully use those ingredients (but it's not mandatory).
"""

DISCOVER_USER_TEMPLATE = """\
Theme / keywords for internet search: {keywords}

Dish types they like: {dish_list}
Diet filters: {diet_list}
Maximum total time in minutes (optional): {max_time}

Ingredients they have / care about (optional free text): {ingredients_text}

Output language: {output_lang}

Return exactly this JSON (1 or 2 recipes):
{{
  "recipes": [
    {{ "title": "<recipe title in {output_lang}>", "ingredients": ["...", "..."], "steps": ["...", "..."] }},
    ...
  ]
}}
"""


def suggest_recipes_from_preferences(
    dish_types: list[str] | None = None,
    diet_filters: list[str] | None = None,
    max_time_minutes: int | None = None,
    target_language: str = "en",
    keywords: str | None = None,
    ingredients_text: str | None = None,
) -> list[dict]:
    """
    Return 1-2 suggested recipes matching preferences: [{ title, ingredients, steps }, ...].
    Raises RuntimeError on missing API key or rate limit.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")
    dish_list = ", ".join((s or "").strip() for s in (dish_types or []) if (s or "").strip()) or "any"
    diet_list = ", ".join((s or "").strip() for s in (diet_filters or []) if (s or "").strip()) or "none"
    max_time = str(max_time_minutes) if max_time_minutes and max_time_minutes > 0 else "no limit"
    keywords_text = (keywords or "").strip() or "none specified"
    ingredients_focus = (ingredients_text or "").strip() or "none specified"
    output_lang = _output_lang_name(target_language)
    prompt = DISCOVER_USER_TEMPLATE.format(
        dish_list=dish_list,
        diet_list=diet_list,
        max_time=max_time,
        keywords=keywords_text,
        ingredients_text=ingredients_focus,
        output_lang=output_lang,
    )
    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": DISCOVER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
            temperature=0.5,
        )
    except RateLimitError as e:
        raise RuntimeError("OpenAI rate limit exceeded, please try again later.") from e
    except APIError as e:
        msg = str(e)
        if "insufficient_quota" in msg or "exceeded your current quota" in msg:
            raise RuntimeError("OpenAI quota exceeded.") from e
        raise
    content = response.choices[0].message.content
    if not content:
        return []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    recipes = data.get("recipes") or data.get("suggestions") or []
    out = []
    for r in recipes[:2]:
        if isinstance(r, dict) and r.get("title"):
            out.append({
                "title": str(r.get("title", "")).strip(),
                "ingredients": [str(x).strip() for x in r.get("ingredients", []) if x],
                "steps": [str(x).strip() for x in r.get("steps", []) if x],
                "missing_ingredients": None,
            })
    return out
