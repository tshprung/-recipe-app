"""AI-generated weekly meal plan (5–7 days)."""
import json
import os

from openai import APIError, OpenAI, RateLimitError

from .what_can_i_make_ai import (
    _diet_list_for_prompt,
    recipe_complies_with_allergens,
    recipe_complies_with_diets,
)

MEAL_PLAN_SYSTEM_PROMPT = """\
You are a meal-planning assistant. Generate a weekly meal plan: one meal per day for 5–7 days.

Rules:
- Output valid JSON only — no markdown, no prose outside the JSON.
- Each day must have: date (YYYY-MM-DD), and one meal with: name, short_description, estimated_time_minutes, title, ingredients (list of strings), steps (list of strings).
- CRITICAL — Diet: Every meal must comply with the user's diet filters (e.g. kosher = no meat+dairy mix; vegetarian = no meat/fish; dairy-free = no milk/cheese).
- CRITICAL — Allergens: Meals must NOT contain any allergen in any form (including optional alternatives like "water or milk" when milk is an allergen).
- Variety: Avoid repeating the same dish type on consecutive days.
- Keep recipes practical and easy to follow.
- Use the requested output language and measurement system.
"""

MEAL_PLAN_USER_TEMPLATE = """\
Generate a {num_days}-day meal plan starting {start_date}.

Constraints:
- Diet: {diet_list}
- Allergens to avoid: {allergen_list}
- Other avoid terms: {avoid_terms}
- Household: {household}
- Max time per meal (minutes): {max_time}
- Budget: {budget}

Output language: {output_lang}
Measurement: {measurement_units} (use g, kg, ml, L for metric; oz, lb, cups, tbsp, tsp for imperial).

Return exactly this JSON (one meal per day):
{{
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "meal": {{
        "name": "Display name",
        "short_description": "One sentence.",
        "estimated_time_minutes": 30,
        "title": "Recipe title",
        "ingredients": ["...", "..."],
        "steps": ["...", "..."]
      }}
    }},
    ...
  ]
}}
"""


def generate_weekly_meal_plan(
    num_days: int = 7,
    start_date: str,
    diet_filters: list[str] | None = None,
    allergens: list[str] | None = None,
    custom_avoid_text: str | None = None,
    household_adults: int | None = None,
    household_kids: int | None = None,
    max_time_minutes: int | None = None,
    budget: str | None = None,
    target_language: str = "en",
    measurement_system: str = "metric",
) -> list[dict]:
    """
    Return a list of day entries: [ {"date": "YYYY-MM-DD", "meal": { name, short_description, estimated_time_minutes, title, ingredients, steps } }, ... ].
    Raises RuntimeError on missing API key or rate limit.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")

    num_days = max(5, min(7, num_days))
    diet_list = _diet_list_for_prompt(diet_filters)
    allergen_list = ", ".join((s or "").strip() for s in (allergens or []) if (s or "").strip()) or "none"
    avoid_terms = (custom_avoid_text or "").strip() or "none"
    household = "any"
    if household_adults is not None or household_kids is not None:
        a = household_adults or 0
        k = household_kids or 0
        household = f"{a} adults, {k} kids"
    max_time = str(max_time_minutes) if max_time_minutes and max_time_minutes > 0 else "no limit"
    budget_str = (budget or "").strip() or "no constraint"
    output_lang = "English"
    if (target_language or "").strip().lower() in ("pl", "he", "es", "fr", "de"):
        output_lang = {"pl": "Polish", "he": "Hebrew", "es": "Spanish", "fr": "French", "de": "German"}.get(
            (target_language or "").strip().lower(), "English"
        )
    measurement_units = "imperial" if (measurement_system or "").strip().lower() == "imperial" else "metric"

    prompt = MEAL_PLAN_USER_TEMPLATE.format(
        num_days=num_days,
        start_date=start_date,
        diet_list=diet_list,
        allergen_list=allergen_list,
        avoid_terms=avoid_terms,
        household=household,
        max_time=max_time,
        budget=budget_str,
        output_lang=output_lang,
        measurement_units=measurement_units,
    )

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": MEAL_PLAN_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=4000,
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

    raw_days = data.get("days") or []
    avoid_terms_list = [p.strip() for p in (custom_avoid_text or "").split(",") if (p or "").strip()] or None
    out = []
    for day in raw_days[:7]:
        if not isinstance(day, dict):
            continue
        date_val = day.get("date") or ""
        meal = day.get("meal")
        if not isinstance(meal, dict) or not meal.get("title"):
            continue
        rec = {
            "title": str(meal.get("title", "")).strip(),
            "ingredients": [str(x).strip() for x in meal.get("ingredients", []) if x],
            "steps": [str(x).strip() for x in meal.get("steps", []) if x],
        }
        if not recipe_complies_with_diets(rec, diet_filters):
            continue
        if not recipe_complies_with_allergens(rec, allergens, avoid_terms_list):
            continue
        out.append({
            "date": date_val,
            "meal": {
                "name": str(meal.get("name") or meal.get("title") or "").strip(),
                "short_description": str(meal.get("short_description") or "").strip(),
                "estimated_time_minutes": int(meal.get("estimated_time_minutes") or 30),
                "title": rec["title"],
                "ingredients": rec["ingredients"],
                "steps": rec["steps"],
            },
        })
    return out


def generate_single_meal(
    diet_filters: list[str] | None = None,
    allergens: list[str] | None = None,
    custom_avoid_text: str | None = None,
    max_time_minutes: int | None = None,
    target_language: str = "en",
    measurement_system: str = "metric",
) -> dict | None:
    """
    Generate one meal (for replacing a day in the plan). Returns { name, short_description, estimated_time_minutes, title, ingredients, steps } or None.
    """
    from .what_can_i_make_ai import suggest_recipes_from_preferences

    recipes = suggest_recipes_from_preferences(
        dish_types=None,
        diet_filters=diet_filters,
        max_time_minutes=max_time_minutes,
        target_language=target_language or "en",
        keywords="dinner",
        ingredients_text=None,
        measurement_system=measurement_system or "metric",
        allergens=allergens,
        custom_avoid_text=custom_avoid_text,
    )
    if not recipes:
        return None
    r = recipes[0]
    return {
        "name": r.get("title") or "Meal",
        "short_description": "",
        "estimated_time_minutes": 30,
        "title": r.get("title") or "",
        "ingredients": r.get("ingredients") or [],
        "steps": r.get("steps") or [],
    }
