import json
import os

from openai import OpenAI

CATEGORIES = ["Warzywa i owoce", "Nabiał", "Mięso i ryby", "Przyprawy i sosy", "Inne"]

SYSTEM_PROMPT = (
    "You are a grocery shopping assistant. "
    "Always respond with valid JSON only — no markdown, no prose outside the JSON."
)

USER_PROMPT_TEMPLATE = """\
You will receive a list of ingredients from one or more recipes (all in Polish).

Your tasks:
1. Merge similar ingredients and sum their quantities where possible.
   Examples: "2 ząbki czosnku" + "3 ząbki czosnku" → "5 ząbków czosnku"
             "1 cebula" + "1 cebula" → "2 cebule"
   If quantities cannot be summed (different units, vague amounts), keep both or list together sensibly.
2. Classify each merged ingredient into exactly one of these categories:
   {categories}

Return a JSON object where each key is a category name and the value is a list of merged ingredient strings.
Every category key must be present even if its list is empty.

Ingredients:
{ingredients}
"""


def categorize_ingredients(ingredients: list[str]) -> dict:
    """Merge similar ingredients, sum quantities, and categorize into Polish grocery categories.

    Returns a dict with all five category keys, each mapping to a list of strings.
    Raises RuntimeError if OPENAI_API_KEY missing, ValueError on bad JSON.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")

    if not ingredients:
        return {cat: [] for cat in CATEGORIES}

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    categories=", ".join(f'"{c}"' for c in CATEGORIES),
                    ingredients="\n".join(f"- {i}" for i in ingredients),
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = response.choices[0].message.content
    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {e}") from e

    return {cat: result.get(cat, []) for cat in CATEGORIES}
