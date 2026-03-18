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
        if diet == "low_fat":
            # Best-effort heuristic: avoid common high-fat cooking methods and ingredients.
            if re.search(r"\b(deep[\s-]?fried|deep[\s-]?fry|fried|bacon|mayonnaise|mayo)\b", text, re.IGNORECASE):
                return False
            if re.search(r"\b(heavy cream|double cream|butter|cheese)\b", text, re.IGNORECASE):
                return False
        if diet == "fat_free":
            # Best-effort heuristic: stricter than low_fat; reject obvious fat sources.
            if re.search(r"\b(oil|olive oil|butter|cheese|cream|mayonnaise|mayo|bacon)\b", text, re.IGNORECASE):
                return False
        if diet == "for_kids_under_1":
            if re.search(r"\b(honey)\b", text, re.IGNORECASE):
                return False
            if re.search(r"\b(whole\s+nut|whole\s+peanut|whole\s+almond|whole\s+walnut)\b", text, re.IGNORECASE):
                return False
            adult_dish = re.search(
                r"\b(taco|tacos|burrito|fajita|burger|pizza|spicy|chili\s+pepper|hot\s+sauce|crispy)\b",
                text,
                re.IGNORECASE,
            )
            if adult_dish:
                return False
        if diet == "for_kids":
            if re.search(r"\b(alcohol|cocktail|wine|beer|spirits|rum|vodka)\b", text, re.IGNORECASE):
                return False
    return True


# Allergen code -> regex of forbidden ingredient keywords (no optional exception).
_ALLERGEN_KEYWORDS = {
    "milk": re.compile(
        r"\b(milk|cream|butter|cheese|yogurt|yoghurt|whey|parmesan|mozzarella|ricotta|feta|cheddar|gouda)\b",
        re.IGNORECASE,
    ),
    "eggs": re.compile(r"\b(egg|eggs)\b", re.IGNORECASE),
    "fish": re.compile(r"\b(fish|salmon|tuna|cod|trout|sardine|anchovy)\b", re.IGNORECASE),
    "crustaceans": re.compile(r"\b(shrimp|prawn|crab|lobster|crayfish)\b", re.IGNORECASE),
    "molluscs": re.compile(r"\b(mussel|oyster|clam|squid|calamari|scallop)\b", re.IGNORECASE),
    "peanuts": re.compile(r"\b(peanut|peanuts)\b", re.IGNORECASE),
    "tree_nuts": re.compile(
        r"\b(almond|walnut|hazelnut|cashew|pecan|pistachio|macadamia|brazil nut)\b",
        re.IGNORECASE,
    ),
    "soybeans": re.compile(r"\b(soy|soya|tofu|edamame)\b", re.IGNORECASE),
    "gluten_cereals": re.compile(
        r"\b(wheat|barley|rye|flour|breadcrumb|pasta|noodle)\b",
        re.IGNORECASE,
    ),
    "celery": re.compile(r"\b(celery)\b", re.IGNORECASE),
    "mustard": re.compile(r"\b(mustard)\b", re.IGNORECASE),
    "sesame": re.compile(r"\b(sesame)\b", re.IGNORECASE),
    "sulphites": re.compile(r"\b(sulphite|sulfite|wine vinegar)\b", re.IGNORECASE),
    "lupin": re.compile(r"\b(lupin|lupini)\b", re.IGNORECASE),
}


def recipe_complies_with_allergens(
    recipe: dict,
    allergen_codes: list[str] | None,
    avoid_terms: list[str] | None,
) -> bool:
    """
    Return True only if the recipe contains none of the given allergens or avoid terms.
    Checks full recipe text; no exception for optional ingredients (e.g. "water or milk" fails when milk is an allergen).
    """
    if not allergen_codes and not avoid_terms:
        return True
    text = _recipe_text(recipe)
    for code in allergen_codes or []:
        c = (code or "").strip().lower()
        if not c:
            continue
        pattern = _ALLERGEN_KEYWORDS.get(c)
        if pattern and pattern.search(text):
            return False
    if avoid_terms:
        for phrase in avoid_terms:
            p = (phrase or "").strip()
            if not p:
                continue
            if p.lower() in text:
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


def _diet_list_for_prompt(diet_filters: list[str] | None) -> str:
    """Build human-readable diet list for discover prompt (expand for_kids/for_kids_under_1)."""
    if not diet_filters:
        return "none"
    expanded = []
    for d in diet_filters:
        s = (d or "").strip()
        if not s:
            continue
        low = s.lower()
        if low == "for_kids_under_1":
            expanded.append("for_kids_under_1 (baby-safe: no honey, no whole nuts, soft textures, no added salt/sugar)")
        elif low == "for_kids":
            expanded.append("for_kids (family-friendly, no alcohol)")
        else:
            expanded.append(s)
    return ", ".join(expanded) if expanded else "none"


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
- Each recipe must have: title, ingredients (list of strings), steps (list of strings), estimated_calories (integer, kcal, rough estimate).
- CRITICAL — Diet compliance: If the user selects a diet (e.g. kosher, vegetarian, vegan), the ENTIRE recipe must comply.
  - Kosher: no pork/bacon/ham, no shellfish; never mix meat and dairy in the same recipe (no cheese with beef/chicken, etc.).
  - Vegetarian: no meat, no fish, no poultry.
  - Vegan: no animal products (no meat, fish, dairy, eggs, honey).
  - Dairy-free: no milk, cream, butter, cheese.
  - for_kids_under_1: Recipes must be suitable for babies roughly 6–12 months. No honey, no whole nuts or choking-risk ingredients, no added salt or sugar, soft/mashable/pureed textures only. Examples: simple vegetable or fruit purees, soft mashes, very soft finger foods. NOT adult-style dishes (no tacos, burgers, pizza, stir-fries, spicy or crispy foods).
  - for_kids: Family-friendly and age-appropriate; avoid heavy spice, alcohol, and obviously adult-only preparations.
  A recipe that only has the diet word in the title but violates it in ingredients/steps is NOT acceptable.
- CRITICAL — Allergens/avoid: If the user lists allergens or avoid terms, the recipe must NOT contain any of those ingredients in ANY form—not even as an optional alternative (e.g. "water or milk" is forbidden when milk is an allergen).
- Respect \"avoid\" terms as best you can.
- Keep recipes practical, clear, and easy to follow.
- If ingredients_text is provided, prefer recipes that meaningfully use those ingredients (but it's not mandatory).
"""

DISCOVER_USER_TEMPLATE = """\
Theme / keywords for internet search: {keywords}

Dish types they like: {dish_list}
Diet filters: {diet_list}
Servings / people to cook for: {servings}
Maximum total time in minutes (optional): {max_time}

Allergens to avoid (must NOT appear in recipe in any form, including optional): {allergen_list}
Other avoid terms (free text): {avoid_terms}

Ingredients they have / care about (optional free text): {ingredients_text}

Output language: {output_lang}

Measurement units: {measurement_units}
- If metric: use grams (g), kilograms (kg), milliliters (ml), liters (L).
- If imperial: use ounces (oz), pounds (lb), cups, tablespoons (tbsp), teaspoons (tsp).

Return exactly this JSON (up to {num_recipes} recipes):
{{
  "recipes": [
    {{ "title": "<recipe title in {output_lang}>", "estimated_calories": 650, "ingredients": ["...", "..."], "steps": ["...", "..."] }},
    ...
  ]
}}
"""


def suggest_recipes_from_preferences(
    dish_types: list[str] | None = None,
    diet_filters: list[str] | None = None,
    num_recipes: int = 3,
    servings: int | None = None,
    max_time_minutes: int | None = None,
    target_language: str = "en",
    keywords: str | None = None,
    ingredients_text: str | None = None,
    measurement_system: str = "metric",
    allergens: list[str] | None = None,
    custom_avoid_text: str | None = None,
) -> list[dict]:
    """
    Return up to N suggested recipes matching preferences: [{ title, ingredients, steps }, ...].
    Raises RuntimeError on missing API key or rate limit.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")
    dish_list = ", ".join((s or "").strip() for s in (dish_types or []) if (s or "").strip()) or "any"
    diet_list = _diet_list_for_prompt(diet_filters)
    allergen_list = ", ".join((s or "").strip() for s in (allergens or []) if (s or "").strip()) or "none"
    avoid_terms = (custom_avoid_text or "").strip() or "none"
    max_time = str(max_time_minutes) if max_time_minutes and max_time_minutes > 0 else "no limit"
    keywords_text = (keywords or "").strip() or "none specified"
    ingredients_focus = (ingredients_text or "").strip() or "none specified"
    output_lang = _output_lang_name(target_language)
    measurement_units = "imperial" if (measurement_system or "").strip().lower() == "imperial" else "metric"
    servings_str = str(int(servings)) if servings is not None and int(servings) > 0 else "default"
    prompt = DISCOVER_USER_TEMPLATE.format(
        dish_list=dish_list,
        diet_list=diet_list,
        num_recipes=str(max(1, min(10, int(num_recipes or 3)))),
        servings=servings_str,
        max_time=max_time,
        allergen_list=allergen_list,
        avoid_terms=avoid_terms,
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
    n = max(1, min(10, int(num_recipes or 3)))
    for r in recipes[:n]:
        if isinstance(r, dict) and r.get("title"):
            calories_raw = r.get("estimated_calories", r.get("calories"))
            try:
                calories = int(calories_raw) if calories_raw is not None else None
                if calories is not None and (calories < 50 or calories > 4000):
                    calories = None
            except Exception:
                calories = None
            rec = {
                "title": str(r.get("title", "")).strip(),
                "estimated_calories": calories,
                "ingredients": [str(x).strip() for x in r.get("ingredients", []) if x],
                "steps": [str(x).strip() for x in r.get("steps", []) if x],
                "missing_ingredients": None,
            }
            # Only include recipes that comply with diets and allergens (full recipe check).
            if not recipe_complies_with_diets(rec, diet_filters):
                continue
            avoid_terms_list = [p.strip() for p in (custom_avoid_text or "").split(",") if (p or "").strip()]
            if not recipe_complies_with_allergens(rec, allergens, avoid_terms_list if avoid_terms_list else None):
                continue
            out.append(rec)
    return out
