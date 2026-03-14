import json
import os

from openai import APIError, OpenAI, RateLimitError

DETECT_PROMPT = """\
Detect the language of this recipe text. Reply with ONLY the ISO 639-1 two-letter code (e.g. he, pl, en, ar, es). Nothing else."""

CLASSIFY_PROMPT = """\
You are a classifier. Decide if the input is a cooking recipe (ingredients + steps) or not.

Return ONLY valid JSON:
{ "is_recipe": true|false }
"""

SYSTEM_PROMPT = (
    "You are a professional recipe translator. "
    "You translate recipes between any languages and adapt ingredients for the target market. "
    "Your most important job is ingredient localisation: every ingredient in the output "
    "MUST be something a home cook can buy in the target market. "
    "Never leave brand names or unavailable ingredients unchanged — replace with generic or local equivalents. "
    "Always respond with valid JSON only — no markdown, no prose outside the JSON."
)

# Country code -> ISO 639-1 language code for "local" shopper language
COUNTRY_TO_LOCAL_LANG = {
    "PL": "pl", "IL": "he", "US": "en", "GB": "uk", "DE": "de", "FR": "fr",
    "ES": "es", "IT": "it", "PT": "pt", "NL": "nl", "RU": "ru", "UA": "uk",
    "TR": "tr", "AR": "ar", "JP": "ja", "CN": "zh", "IN": "hi", "BR": "pt",
}
LANG_DISPLAY_NAMES = {
    "en": "English", "pl": "Polish", "he": "Hebrew", "de": "German", "fr": "French",
    "es": "Spanish", "it": "Italian", "pt": "Portuguese", "ru": "Russian", "uk": "Ukrainian",
    "tr": "Turkish", "ar": "Arabic", "ja": "Japanese", "zh": "Chinese", "hi": "Hindi",
}

USER_PROMPT_TEMPLATE = """\
Translate this recipe from {source_lang} to {target_lang} for a cook in {target_country}.
Apply localisation rules for that country's market (ingredient names, brands, units). Use country-level context (e.g. common supermarkets in Poland: Lidl, Biedronka, Carrefour) rather than a specific city.

CRITICAL: The output language for ALL user-facing text (title, ingredients, steps, tags, substitutions) MUST be {target_lang}. The JSON key names (title_pl, ingredients_pl, steps_pl) are legacy and do NOT mean Polish — write in {target_lang} only. If target_lang is "en", output English. If target_lang is "pl", output Polish. No exceptions.

INGREDIENT PARENTHETICAL: For each ingredient in ingredients_pl, output the name in {target_lang}. If the shopper's local language ({local_lang_name}) is different from the recipe language ({recipe_lang_name}), add in parentheses: the same ingredient name in the local language, written phonetically in the script of the recipe language, then a comma and the recipe language name in {target_lang}. Examples: recipe English, local Polish → "cilantro (kolendra, English)"; recipe Hebrew, local Polish → "כוסברה (קולנדרה, פולנית)". Only add the parenthetical when the two languages differ; if they are the same, output just the ingredient name.

Return a single JSON object with EXACTLY these keys:

{{
  "title_pl": "<recipe title in {target_lang}>",
  "title_original": "<original recipe title as it appears in the source>",
  "prep_time_minutes": <integer minutes or null>,
  "cook_time_minutes": <integer minutes or null>,
  "ingredients_pl": [
    "<quantity + ingredient name in {target_lang}>" or "<quantity + name (local name in recipe script, recipe lang label)>",
    ...
  ],
  "ingredients_original": [
    "<exact ingredient line from the source recipe>",
    ...
  ],
  "steps_pl": [
    "<step 1 in {target_lang} — clear, complete sentence>",
    ...
  ],
  "tags": ["<short tag in {target_lang}>", ...],
  "substitutions": {{
    "<source ingredient>": "<target market equivalent widely available in {target_country}>"
  }},
  "notes": {{
    "porcje": "<servings — only if stated>",
    "czas_przygotowania": "<prep time — only if stated>",
    "czas_gotowania": "<cook time — only if stated>"
  }}
}}

Rules:
- Write ALL of title_pl, ingredients_pl, steps_pl, and tags in {target_lang} only. Ignore the "_pl" in key names.
- ingredients_original: copy each ingredient line exactly as in the source.
- substitutions: in {target_lang}; localise for {target_country}.
- notes: include ONLY keys explicitly mentioned in the source. Omit the rest.
- prep_time_minutes / cook_time_minutes: if the recipe states prep/cook time, convert to TOTAL MINUTES as integers; otherwise null.
- If the input is not a recipe, DO NOT invent steps. Keep output minimal and truthful.

Recipe in {source_lang}:
---
{raw_input}
---
"""


def detect_language(raw_input: str, client: OpenAI) -> str:
    """Detect recipe language; returns ISO 639-1 code (e.g. he, pl, en)."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": DETECT_PROMPT + "\n\n" + (raw_input[:2000] or " ")},
        ],
        temperature=0,
    )
    code = (response.choices[0].message.content or "").strip().lower()[:10]
    # Normalise to ISO 639-1
    if not code or not code.isalpha():
        return "en"
    return code[:2] if len(code) >= 2 else code


def _is_recipe(raw_input: str, client: OpenAI) -> bool:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": CLASSIFY_PROMPT + "\n\n" + (raw_input[:4000] or " ")},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return True  # fail-open to avoid blocking valid recipes
    return bool(data.get("is_recipe", True))


def translate_recipe(
    raw_input: str,
    target_language: str,
    target_country: str,
    target_city: str,
) -> dict:
    """
    Detect source language, then translate recipe to target language with localisation.
    Returns the same JSON shape as before; callers can read detected_language from the result
    if we add it to the response, or we detect inside and pass it to the translate prompt.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")

    client = OpenAI(api_key=api_key)

    def _looks_like_recipe_heuristic(text: str) -> bool:
        """Heuristic fallback so obviously recipe-like text is accepted even if classifier is unsure."""
        lowered = (text or "").lower()
        keywords = [
            "ingredients",
            "ingredienti",
            "sk\u0142adniki",  # PL
            "\u05de\u05e6\u05e8\u05db\u05d9\u05dd",  # he: ingredients
            "instructions",
            "preparation",
            "\u05d4\u05d5\u05e8\u05d0\u05d5\u05ea \u05d4\u05db\u05e0\u05d4",  # he: preparation steps
            "step 1",
            "step 2",
        ]
        if any(k in lowered for k in keywords):
            return True
        # Long-ish text with numbered steps is very likely to be a recipe.
        if lowered.count("\n") >= 5 and any(token in lowered for token in ["1.", "2.", "3."]):
            return True
        return False

    if not _is_recipe(raw_input, client) and not _looks_like_recipe_heuristic(raw_input):
        raise ValueError("NOT_A_RECIPE: classifier=false")
    source_lang = detect_language(raw_input, client)

    local_lang = COUNTRY_TO_LOCAL_LANG.get((target_country or "").strip().upper()) or target_language
    recipe_lang_name = LANG_DISPLAY_NAMES.get((target_language or "").strip().lower(), (target_language or "English"))
    local_lang_name = LANG_DISPLAY_NAMES.get((local_lang or "").strip().lower(), (local_lang or ""))

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(
                        source_lang=source_lang,
                        target_lang=target_language,
                        target_country=target_country,
                        raw_input=raw_input,
                        recipe_lang_name=recipe_lang_name,
                        local_lang_name=local_lang_name,
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
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
    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {e}") from e

    result["detected_language"] = source_lang
    return result


EXTRACT_RECIPES_SYSTEM = """You are extracting recipes from a webpage.

Your goal is to detect ALL complete recipes that appear on the page.

Definition of a recipe: A recipe is any section that contains BOTH (1) a list of ingredients and (2) preparation instructions/steps.

Rules:
1. Do NOT assume there is only one recipe per page. Scan the entire page and detect every ingredients + instructions pair.
2. If multiple ingredient sections exist with their own preparation steps, treat them as separate recipes.
3. Never merge two distinct recipes into one. If the page has two (or more) separate recipes—each with its own ingredients and steps—you MUST return two (or more) separate objects in the array. One array element per recipe.
4. Use repeated structure to find boundaries: look for a heading or title followed by an ingredient list and then preparation steps. Each such block is one recipe. This applies in any language (e.g. Hebrew מתכון 1 / מתכון 2, or "Recipe 1" / "Recipe 2").

Sub-recipe detection: If the page contains components such as sauce, salad, topping, filling, frosting, side dish, and that component includes its own ingredients and preparation steps, extract it as a separate recipe.
- SPLIT examples: Pancakes + Fruit Salad; Cake + Frosting; Burger + Sauce; Salad + Dressing.
- Keep ONE recipe when: "For the cake" + "For the frosting" are clearly part of assembling the same dessert; marinade used directly in the same cooking process.

Structure: Each recipe must be returned independently. Do not share ingredients between recipes unless the page explicitly repeats them.

Ignore: links to other pages, recommended recipes, lists of related recipes, advertisements. Only extract recipes fully present on the current page.

Quality: Include only sections that have BOTH ingredients and instructions. Discard ingredients-only or instructions-only sections.
Use headings (H1–H4) that precede an ingredient list as potential recipe titles. Detect ingredient lists by bullet/numbered lists and quantities (g, ml, cups, tbsp, tsp).
"""

EXTRACT_RECIPES_OUTPUT = """Return a JSON array only. No markdown, no explanation.
If you see "Recipe A" with ingredients and steps, then "Recipe B" with different ingredients and steps, return exactly 2 objects.
[
  {
    "title": "Recipe title",
    "ingredients": ["ingredient 1", "ingredient 2"],
    "instructions": ["step 1", "step 2"]
  }
]
Verify each recipe has both ingredients and instructions before including. If none found, return []."""


def extract_recipes_from_page(page_text: str) -> list[dict]:
    """
    Extract all complete recipes from page text. Returns list of
    {"title": str, "ingredients": list[str], "instructions": list[str]}.
    Only includes items that have both ingredients and instructions.
    When OPENAI_API_KEY is unset, returns empty list (caller may fall back to whole page).
    """
    if not (page_text or "").strip():
        return []
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []  # No AI; split_page_into_recipes will fall back to whole page
    client = OpenAI(api_key=api_key)
    text = (page_text or "").strip()[:15000]
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EXTRACT_RECIPES_SYSTEM},
                {"role": "user", "content": EXTRACT_RECIPES_OUTPUT + "\n\nPage text:\n---\n" + text + "\n---"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        data = json.loads(content)
        # Accept either top-level array or { "recipes": [...] }
        recipes = data if isinstance(data, list) else data.get("recipes")
        if not isinstance(recipes, list):
            return []
        out = []
        for r in recipes:
            if not isinstance(r, dict):
                continue
            title = (r.get("title") or "").strip() or "Untitled"
            ingredients = r.get("ingredients") or r.get("ingredients_pl") or []
            instructions = r.get("instructions") or r.get("steps") or r.get("steps_pl") or []
            if not isinstance(ingredients, list):
                ingredients = []
            if not isinstance(instructions, list):
                instructions = []
            ingredients = [str(x).strip() for x in ingredients if x]
            instructions = [str(x).strip() for x in instructions if x]
            if not ingredients or not instructions:
                continue
            out.append({"title": title, "ingredients": ingredients, "instructions": instructions})
        return out
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def _structured_recipe_to_raw_input(recipe: dict) -> str:
    """Convert extracted {title, ingredients, instructions} to raw text for translate_recipe."""
    title = (recipe.get("title") or "").strip() or "Untitled"
    ingredients = recipe.get("ingredients") or []
    instructions = recipe.get("instructions") or []
    lines_ing = "\n".join(f"- {s}" for s in ingredients if s)
    lines_steps = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(instructions) if s)
    return f"{title}\n\nIngredients:\n{lines_ing}\n\nSteps:\n{lines_steps}"


def split_page_into_recipes(page_text: str) -> list[str]:
    """
    Extract all complete recipes from the page (including sub-recipes like sauce, frosting)
    and return one raw text chunk per recipe for translation.
    When extraction returns nothing (e.g. no API key), falls back to whole page as one chunk.
    """
    if not (page_text or "").strip():
        return []
    structured = extract_recipes_from_page(page_text)
    if not structured:
        return [(page_text or "").strip()]
    return [_structured_recipe_to_raw_input(r) for r in structured]
