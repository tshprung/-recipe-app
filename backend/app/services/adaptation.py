import json
import os

import anthropic

DIET_LABELS = {
    "vegetarian": "wegetariańskim (bez mięsa i ryb)",
    "vegan": "wegańskim (bez produktów odzwierzęcych)",
    "dairy_free": "bez nabiału (bez mleka, sera, masła, śmietany)",
    "gluten_free": "bez glutenu (bez pszenicy, żyta, jęczmienia, owsa)",
    "kosher": "koszernym (zasady kaszrutu)",
}

SYSTEM_PROMPT = (
    "You are a professional recipe adaptation assistant. "
    "Given a Polish recipe, adapt it to a specified diet. "
    "Preserve the dish's character as much as possible. "
    "Always respond with valid JSON only — no markdown, no prose outside the JSON."
)

ADAPTED_TEMPLATE = """\
Adapt this Polish recipe to be {diet_label}.

Rules:
- ALWAYS attempt to replace every non-compliant ingredient with the closest compliant Polish supermarket equivalent.
- If a suitable substitute exists, use it — never leave a non-compliant ingredient unchanged without flagging it.
- If an individual ingredient truly cannot be substituted (no acceptable replacement exists):
    * Keep the ingredient in ingredients_pl as-is (do NOT remove it silently).
    * Add a warning string to the "ostrzeżenia" list in "notes":
      "Nie znaleziono zamiennika dla: [ingredient name]. Rozważ pominięcie."
- Set "can_adapt": false ONLY when the dish's ENTIRE identity depends on a non-compliant ingredient
  (e.g. the whole dish is a meat roast and there is truly no plant-based version).
  In that case provide 2-3 actionable alternatives, each with:
    - "title": short Polish name (e.g. "Wersja z rybą")
    - "reason": one sentence why this works
    - "instruction": precise English instruction to pass back for re-adaptation
- If adaptation is possible (even partially), always set "can_adapt": true.

Kosher-specific rules (when diet is kosher):
- No mixing meat + dairy — if the recipe has both, set can_adapt=false and offer:
  1. A meat version (remove all dairy)
  2. A dairy version (remove all meat)
- No pork → substitute with beef, chicken, or turkey
- No shellfish → substitute with fish or omit
- Flag ingredients needing kosher certification (wine, vinegar, gelatin) in notes

Return JSON with exactly this shape:
{{
  "can_adapt": true,
  "title_pl": "...",
  "ingredients_pl": ["..."],
  "steps_pl": ["..."],
  "notes": {{"ostrzeżenia": []}},
  "alternatives": []
}}
OR if cannot adapt:
{{
  "can_adapt": false,
  "title_pl": null,
  "ingredients_pl": [],
  "steps_pl": [],
  "notes": {{}},
  "alternatives": [
    {{"title": "...", "reason": "...", "instruction": "..."}}
  ]
}}

Recipe title: {title}
Ingredients:
{ingredients}

Steps:
{steps}
"""

CUSTOM_TEMPLATE = """\
Adapt this Polish recipe using the following instruction: {instruction}

Rules:
- Apply the instruction faithfully while keeping as much of the original recipe's character as possible.
- Use Polish supermarket equivalents for any new ingredients.
- Return the full adapted recipe — do not leave anything out.

Return JSON with exactly this shape:
{{
  "can_adapt": true,
  "title_pl": "...",
  "ingredients_pl": ["..."],
  "steps_pl": ["..."],
  "notes": {{}},
  "alternatives": []
}}

Recipe title: {title}
Ingredients:
{ingredients}

Steps:
{steps}
"""


def _build_recipe_text(recipe) -> tuple[str, str]:
    ingredients_text = "\n".join(
        f"- {ing}" if isinstance(ing, str)
        else f"- {ing.get('amount', '')} {ing.get('name', '')}".strip()
        for ing in (recipe.ingredients_pl or [])
    )
    steps_text = "\n".join(
        f"{i + 1}. {step}" for i, step in enumerate(recipe.steps_pl or [])
    )
    return ingredients_text, steps_text


def adapt_recipe(recipe, variant_type: str, custom_instruction: str | None = None) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured on the server.")

    ingredients_text, steps_text = _build_recipe_text(recipe)

    # Escape curly braces in user data so str.format() doesn't misinterpret them
    def _esc(s: str) -> str:
        return s.replace('{', '{{').replace('}', '}}')

    if custom_instruction:
        prompt = CUSTOM_TEMPLATE.format(
            instruction=_esc(custom_instruction),
            title=_esc(recipe.title_pl),
            ingredients=_esc(ingredients_text),
            steps=_esc(steps_text),
        )
    else:
        diet_label = DIET_LABELS.get(variant_type, variant_type)
        prompt = ADAPTED_TEMPLATE.format(
            diet_label=diet_label,
            title=_esc(recipe.title_pl),
            ingredients=_esc(ingredients_text),
            steps=_esc(steps_text),
        )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text
    # Strip markdown code fences if model wrapped response anyway
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    try:
        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {e}") from e
