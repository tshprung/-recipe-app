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
"""

USER_PROMPT_TEMPLATE = """\
Ingredients the user has: {ingredients}

Diet restrictions: {diet_list}

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
    output_lang = _output_lang_name(target_language)

    prompt = USER_PROMPT_TEMPLATE.format(
        ingredients=ingredients_str,
        diet_list=diet_list,
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
