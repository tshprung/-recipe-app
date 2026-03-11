import json
import os
from string import Template

from openai import APIError, OpenAI, RateLimitError

from .translation import COUNTRY_TO_LOCAL_LANG, LANG_DISPLAY_NAMES

# Language code -> readable name for prompts (so model outputs in correct language)
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
    "cs": "Czech",
    "hu": "Hungarian",
    "ro": "Romanian",
    "el": "Greek",
    "sv": "Swedish",
}

def _lang_name(code: str) -> str:
    return _LANG_NAMES.get((code or "").strip().lower(), "English")

DIET_LABELS = {
    "vegetarian": "vegetarian (no meat or fish)",
    "vegan": "vegan (no animal products)",
    "dairy_free": "dairy-free — replace milk, cream, butter, cheese with plant-based alternatives (e.g. oat/soy milk, plant margarine, coconut cream, vegan cheese or omit)",
    "gluten_free": "gluten-free (no wheat, rye, barley, oats)",
    "kosher": "kosher (kashrut rules)",
    "halal": "halal (Islamic dietary rules)",
    "nut_free": "nut-free (for allergies)",
    "low_sodium": "low-sodium (limited salt)",
}

SYSTEM_PROMPT = (
    "You are a professional recipe adaptation assistant. "
    "Adapt recipes to a specified diet while preserving the dish's character. "
    "Output language is specified in each request — write ALL user-facing text (title, ingredients, steps, adaptation_summary) in that language only. "
    "Prefer common, widely available ingredients for the target market; avoid niche or overly specific products that may not exist locally. "
    "If you use a plant-based meat alternative, keep it generic (e.g. 'mielone roślinne') and you may add 1–2 example brands only as examples (never claim guaranteed availability). "
    "For Poland examples include: Beyond Meat (Beyond Mince), Bezmięsny, The Vegetarian Butcher (roślinne mielone). "
    "Always respond with valid JSON only — no markdown, no prose outside the JSON."
)

ADAPTED_TEMPLATE = Template("""\
Adapt this recipe to be $diet_label.

OUTPUT LANGUAGE: All of title_pl, ingredients_pl, steps_pl, and notes.adaptation_summary MUST be written in $output_lang only. The recipe you receive may be in any language; your output must be entirely in $output_lang.

$ingredient_parenthetical_rule

Rules:
- Replace every non-compliant ingredient with the closest compliant equivalent appropriate for the recipe's market.
- If a suitable substitute exists, use it — never leave a non-compliant ingredient unchanged without flagging it.
- If an individual ingredient truly cannot be substituted: keep it in ingredients_pl as-is and add a warning to "ostrzeżenia" in "notes" (write the warning in $output_lang).
- Set "can_adapt": false ONLY when the dish's ENTIRE identity depends on a non-compliant ingredient. Then provide 2-3 alternatives with "title", "reason", "instruction" (all in $output_lang).
- If adaptation is possible (even partially), always set "can_adapt": true.
- For dairy_free: substitute milk, cream, butter, cheese with plant-based alternatives. Do NOT set can_adapt=false just because the recipe contains dairy.

Kosher: no meat+dairy mixing; if both present offer meat version or dairy version. With dairy_free combined: output one version with plant-based dairy substitutes. No pork → beef/chicken/turkey; no shellfish → fish or omit. Flag wine, vinegar, gelatin in notes.
- In "notes" include "adaptation_summary" in $output_lang: briefly list changes, or "No changes were needed — this recipe already fits this diet."

Return JSON with exactly this shape:
{
  "can_adapt": true,
  "title_pl": "<in $output_lang>",
  "ingredients_pl": ["<each in $output_lang>"],
  "steps_pl": ["<each in $output_lang>"],
  "notes": {"ostrzeżenia": [], "adaptation_summary": "<in $output_lang>"},
  "alternatives": []
}
OR if cannot adapt:
{
  "can_adapt": false,
  "title_pl": null,
  "ingredients_pl": [],
  "steps_pl": [],
  "notes": {},
  "alternatives": [{"title": "...", "reason": "...", "instruction": "..."}]
}

Recipe title: $title
Ingredients:
$ingredients

Steps:
$steps
""")

CUSTOM_TEMPLATE = Template("""\
Adapt this recipe using the following instruction: $instruction

OUTPUT LANGUAGE: All of title_pl, ingredients_pl, steps_pl, and notes.adaptation_summary MUST be written in $output_lang only.

$ingredient_parenthetical_rule

Rules:
- Apply the instruction faithfully while keeping the recipe's character. Use market-appropriate equivalents for any new ingredients.
- Return the full adapted recipe. In "notes" include "adaptation_summary" in $output_lang: what was changed, or "No changes were needed."

Return JSON with exactly this shape:
{
  "can_adapt": true,
  "title_pl": "<in $output_lang>",
  "ingredients_pl": ["<in $output_lang>"],
  "steps_pl": ["<in $output_lang>"],
  "notes": {"adaptation_summary": "<in $output_lang>"},
  "alternatives": []
}

Recipe title: $title
Ingredients:
$ingredients

Steps:
$steps
""")


def _get_recipe_attrs(recipe):
    """Recipe can be an ORM model or a dict (for chained adaptations)."""
    if hasattr(recipe, "ingredients_pl"):
        return recipe.title_pl, recipe.ingredients_pl or [], recipe.steps_pl or []
    # dict from a previous adaptation result
    return (
        recipe.get("title_pl", ""),
        recipe.get("ingredients_pl", []),
        recipe.get("steps_pl", []),
    )


def _build_recipe_text(recipe) -> tuple[str, str]:
    _, ingredients_pl, steps_pl = _get_recipe_attrs(recipe)
    ingredients_text = "\n".join(
        f"- {ing}" if isinstance(ing, str)
        else f"- {ing.get('amount', '')} {ing.get('name', '')}".strip()
        for ing in ingredients_pl
    )
    steps_text = "\n".join(
        f"{i + 1}. {step}" for i, step in enumerate(steps_pl)
    )
    return ingredients_text, steps_text


def _ingredient_parenthetical_rule(target_language: str, target_country: str | None) -> str:
    """Instruction for adding local-language parenthetical to ingredients when recipe and local lang differ."""
    if not target_country or not target_country.strip():
        return ""
    local_lang = COUNTRY_TO_LOCAL_LANG.get(target_country.strip().upper()) or target_language
    if (local_lang or "").strip().lower() == (target_language or "").strip().lower():
        return ""
    recipe_lang_name = LANG_DISPLAY_NAMES.get((target_language or "").strip().lower(), target_language or "English")
    local_lang_name = LANG_DISPLAY_NAMES.get((local_lang or "").strip().lower(), local_lang or "")
    return (
        f"INGREDIENT PARENTHETICAL: For each ingredient in ingredients_pl, output the name in the output language. "
        f"Since the shopper's local language ({local_lang_name}) differs from the recipe language ({recipe_lang_name}), "
        f'add in parentheses: the same ingredient name in the local language, written phonetically in the script of the output language, '
        f'then a comma and the recipe language name in the output language. E.g. "cilantro (kolendra, English)" or "כוסברה (קולנדרה, פולנית)".'
    )


def adapt_recipe(
    recipe,
    variant_type: str,
    custom_instruction: str | None = None,
    target_language: str = "en",
    target_country: str | None = None,
) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")

    output_lang = _lang_name(target_language)
    title_pl, _, _ = _get_recipe_attrs(recipe)
    ingredients_text, steps_text = _build_recipe_text(recipe)
    ingredient_rule = _ingredient_parenthetical_rule(target_language, target_country)

    if custom_instruction:
        prompt = CUSTOM_TEMPLATE.safe_substitute(
            instruction=custom_instruction,
            output_lang=output_lang,
            title=title_pl,
            ingredients=ingredients_text,
            steps=steps_text,
            ingredient_parenthetical_rule=ingredient_rule,
        )
    else:
        diet_label = DIET_LABELS.get(variant_type, variant_type)
        prompt = ADAPTED_TEMPLATE.safe_substitute(
            diet_label=diet_label,
            output_lang=output_lang,
            title=title_pl,
            ingredients=ingredients_text,
            steps=steps_text,
            ingredient_parenthetical_rule=ingredient_rule,
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
            max_tokens=2048,
            temperature=0,
        )
    except RateLimitError as e:
        raise RuntimeError("OpenAI rate limit exceeded, please try again later.") from e
    except APIError as e:
        message = str(e)
        if "insufficient_quota" in message or "exceeded your current quota" in message:
            raise RuntimeError(
                "OpenAI quota exceeded, please check your plan and billing."
            ) from e
        raise

    content = response.choices[0].message.content

    # Strip markdown code fences if model wrapped response anyway
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    try:
        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {e}") from e
