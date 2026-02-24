import json
import os

from openai import OpenAI

SYSTEM_PROMPT = (
    "You are a professional recipe translator specialising in Hebrew → Polish translation. "
    "You have deep knowledge of Israeli cuisine, Polish supermarkets (Biedronka, Lidl, Kaufland, "
    "Carrefour, local bazaars), and how to adapt Middle-Eastern recipes for a Polish home cook. "
    "Always respond with valid JSON only — no markdown, no prose outside the JSON."
)

USER_PROMPT_TEMPLATE = """\
Translate the following Hebrew recipe to Polish and return a single JSON object with EXACTLY these keys:

{{
  "title_pl": "<Polish recipe title>",
  "title_original": "<Original Hebrew title extracted from the text>",
  "ingredients_pl": [
    "<quantity + Polish ingredient name, e.g. '2 łyżki tahiny'>",
    ...
  ],
  "ingredients_original": [
    "<exact Hebrew ingredient line copied verbatim from the recipe>",
    ...
  ],
  "steps_pl": [
    "<step 1 in Polish — clear, complete sentence>",
    ...
  ],
  "tags": ["<short Polish tag>", ...],
  "substitutions": {{
    "<Hebrew or Israeli ingredient>": "<Polish equivalent + where to buy in {city}>"
  }},
  "notes": {{
    "porcje": "<servings — include only if stated in the recipe>",
    "czas_przygotowania": "<prep time — include only if stated>",
    "czas_gotowania": "<cook time — include only if stated>"
  }}
}}

Rules:
- ingredients_pl: one string per ingredient, with quantity, fully in Polish.
- ingredients_original: copy each ingredient line exactly as it appears in the Hebrew.
- steps_pl: each cooking step as a separate string, translated fully into Polish.
- tags: 3–5 short Polish tags (e.g. "wegetariański", "kuchnia bliskowschodnia", "szybkie", "bez glutenu").
- substitutions: ONLY include ingredients that are hard to find in Poland. Suggest specific Polish store equivalents available in {city}. Omit common ingredients (eggs, flour, oil, salt, sugar).
- notes: include ONLY keys that are explicitly mentioned in the source recipe. Omit the rest.
- If the input is not a recipe, do your best to extract what you can.

Hebrew recipe:
---
{raw_input}
---
"""


def translate_recipe(raw_input: str, target_city: str = "Wrocław") -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    city=target_city,
                    raw_input=raw_input,
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {e}") from e
