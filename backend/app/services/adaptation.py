import json
import os

from openai import OpenAI

DIET_LABELS = {
    "vegetarian": "wegetariańskim (bez mięsa i ryb)",
    "vegan": "wegańskim (bez produktów odzwierzęcych)",
    "dairy_free": "bez nabiału (bez mleka, sera, masła, śmietany)",
    "gluten_free": "bez glutenu (bez pszenicy, żyta, jęczmienia, owsa)",
    "kosher": "koszernym (zasady kaszrutu: bez wieprzowiny, bez owoców morza, bez mieszania mięsa z nabiałem)",
}

SYSTEM_PROMPT = (
    "You are a professional recipe adaptation assistant. "
    "Given a Polish recipe, adapt it to a specified diet. "
    "Preserve the dish's character as much as possible. "
    "Always respond with valid JSON only — no markdown."
)

ADAPTED_TEMPLATE = """\
Adapt this Polish recipe to be {diet_label}.

Rules:
- Replace any non-compliant ingredients with the closest compliant Polish supermarket equivalent.
- If a core ingredient cannot be replaced (the dish would lose its identity), set "can_adapt": false
  and provide up to 3 alternative recipe suggestions in "alternatives": [{{"title": "...", "reason": "..."}}}].
- If adaptation is possible, set "can_adapt": true and return full adapted recipe.
- Kosher rules: no mixing meat+dairy; no pork/shellfish; flag wine/vinegar/gelatin in substitutions.

Return JSON with exactly this shape:
{{
  "can_adapt": true,
  "title_pl": "...",
  "ingredients_pl": ["..."],
  "steps_pl": ["..."],
  "notes": {{}},
  "alternatives": []
}}
OR if cannot adapt:
{{
  "can_adapt": false,
  "title_pl": null,
  "ingredients_pl": [],
  "steps_pl": [],
  "notes": {{}},
  "alternatives": [{{"title": "...", "reason": "..."}}]
}}

Recipe title: {title}
Ingredients:
{ingredients}

Steps:
{steps}
"""


def adapt_recipe(recipe, variant_type: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")

    diet_label = DIET_LABELS.get(variant_type, variant_type)

    ingredients_text = "\n".join(
        f"- {ing}" if isinstance(ing, str) else f"- {ing.get('amount', '')} {ing.get('name', '')}".strip()
        for ing in (recipe.ingredients_pl or [])
    )
    steps_text = "\n".join(
        f"{i + 1}. {step}" for i, step in enumerate(recipe.steps_pl or [])
    )

    prompt = ADAPTED_TEMPLATE.format(
        diet_label=diet_label,
        title=recipe.title_pl,
        ingredients=ingredients_text,
        steps=steps_text,
    )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {e}") from e
