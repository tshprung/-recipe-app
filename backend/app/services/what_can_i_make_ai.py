"""AI suggestion for 'What can I make' — generate a recipe from ingredients + diet."""
import json
import os
import re

from openai import APIError, OpenAI, RateLimitError


def _recipe_text(recipe: dict) -> str:
    """Full recipe text (title + ingredients + steps) for diet compliance checks."""
    title = (recipe.get("title") or "").strip()
    ingredients = recipe.get("ingredients") or []
    steps = recipe.get("steps") or []
    parts = [title]
    for x in ingredients:
        if x:
            parts.append(str(x).strip())
    for x in steps:
        if x:
            parts.append(str(x).strip())
    return " ".join(parts).lower()


# Keywords for kosher compliance: forbidden or meat+dairy mix.
_PORK_SHELLFISH = re.compile(
    r"\b(pork|bacon|ham|lard|speck|pancetta|prosciutto|"
    r"shrimp|prawn|crab|lobster|crayfish|mussel|oyster|clam|squid|calamari|scallop)\b",
    re.IGNORECASE,
)
_MEAT_KEYWORDS = re.compile(
    r"\b(beef|veal|lamb|chicken|turkey|duck|goose|meat|minced meat|ground beef|"
    r"sausage|chorizo|bacon|ham|pork)\b",
    re.IGNORECASE,
)
_DAIRY_KEYWORDS = re.compile(
    r"\b(cheese|milk|cream|butter|yogurt|yoghurt|whey|parmesan|mozzarella|"
    r"ricotta|feta|cheddar|gouda)\b",
    re.IGNORECASE,
)


def recipe_complies_with_diets(recipe: dict, diet_filters: list[str] | None) -> bool:
    """
    Return True only if the recipe actually complies with all selected diets.
    Checks full recipe text (title, ingredients, steps), not just the title.
    """
    if not diet_filters:
        return True
    text = _recipe_text(recipe)
    for d in diet_filters:
        diet = (d or "").strip().lower()
        if not diet:
            continue
        if diet == "kosher":
            if _PORK_SHELLFISH.search(text):
                return False
            has_meat = bool(_MEAT_KEYWORDS.search(text))
            has_dairy = bool(_DAIRY_KEYWORDS.search(text))
            if has_meat and has_dairy:
                return False
        if diet == "halal":
            if re.search(r"\b(pork|bacon|ham|lard)\b", text, re.IGNORECASE):
                return False
        if diet == "vegetarian":
            if re.search(r"\b(meat|beef|chicken|pork|bacon|ham|fish|tuna|salmon)\b", text, re.IGNORECASE):
                return False
        if diet == "vegan":
            if re.search(
                r"\b(meat|beef|chicken|pork|fish|milk|cream|butter|cheese|egg|honey)\b",
                text,
                re.IGNORECASE,
            ):
                return False
        if diet == "dairy_free":
            if _DAIRY_KEYWORDS.search(text):
                return False
    return True

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
- Use that plus dish types, diets, max cooking time, and important ingredients to imagine up to 3 excellent recipes
  the user could realistically cook at home.

Rules:
- Output valid JSON only — no markdown, no prose outside the JSON.
- Each recipe must have: title, ingredients (list of strings), steps (list of strings).
- CRITICAL — Diet compliance: If the user selects a diet (e.g. kosher, vegetarian, vegan), the ENTIRE recipe must comply.
  - Kosher: no pork/bacon/ham, no shellfish; never mix meat and dairy in the same recipe (no cheese with beef/chicken, etc.).
  - Vegetarian: no meat, no fish, no poultry.
  - Vegan: no animal products (no meat, fish, dairy, eggs, honey).
  - Dairy-free: no milk, cream, butter, cheese.
  A recipe that only has the diet word in the title but violates it in ingredients/steps is NOT acceptable.
- Respect \"avoid\" terms as best you can.
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

Measurement units: {measurement_units}
- If metric: use grams (g), kilograms (kg), milliliters (ml), liters (L).
- If imperial: use ounces (oz), pounds (lb), cups, tablespoons (tbsp), teaspoons (tsp).

Return exactly this JSON (up to 3 recipes):
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
    measurement_system: str = "metric",
) -> list[dict]:
    """
    Return up to 3 suggested recipes matching preferences: [{ title, ingredients, steps }, ...].
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
    measurement_units = "imperial" if (measurement_system or "").strip().lower() == "imperial" else "metric"
    prompt = DISCOVER_USER_TEMPLATE.format(
        dish_list=dish_list,
        diet_list=diet_list,
        max_time=max_time,
        keywords=keywords_text,
        ingredients_text=ingredients_focus,
        output_lang=output_lang,
        measurement_units=measurement_units,
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
    for r in recipes[:3]:
        if isinstance(r, dict) and r.get("title"):
            rec = {
                "title": str(r.get("title", "")).strip(),
                "ingredients": [str(x).strip() for x in r.get("ingredients", []) if x],
                "steps": [str(x).strip() for x in r.get("steps", []) if x],
                "missing_ingredients": None,
            }
            # Only include recipes that actually comply with selected diets (full recipe check).
            if recipe_complies_with_diets(rec, diet_filters):
                out.append(rec)
    return out
