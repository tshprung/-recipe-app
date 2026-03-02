import json
import os

from openai import APIError, OpenAI, RateLimitError

DETECT_PROMPT = """\
Detect the language of this recipe text. Reply with ONLY the ISO 639-1 two-letter code (e.g. he, pl, en, ar, es). Nothing else."""

SYSTEM_PROMPT = (
    "You are a professional recipe translator. "
    "You translate recipes between any languages and adapt ingredients for the target market. "
    "Your most important job is ingredient localisation: every ingredient in the output "
    "MUST be something a home cook can buy in the target market. "
    "Never leave brand names or unavailable ingredients unchanged — replace with generic or local equivalents. "
    "Always respond with valid JSON only — no markdown, no prose outside the JSON."
)

USER_PROMPT_TEMPLATE = """\
Translate this recipe from {source_lang} to {target_lang} for a cook in {city}, {target_country}.
Apply localisation rules for that market (ingredient names, brands, units).

Return a single JSON object with EXACTLY these keys:

{{
  "title_pl": "<recipe title in the target language>",
  "title_original": "<original recipe title as it appears in the source>",
  "ingredients_pl": [
    "<quantity + ingredient name in target language>",
    ...
  ],
  "ingredients_original": [
    "<exact ingredient line from the source recipe>",
    ...
  ],
  "steps_pl": [
    "<step 1 in target language — clear, complete sentence>",
    ...
  ],
  "tags": ["<short tag in target language>", ...],
  "substitutions": {{
    "<source ingredient>": "<target market equivalent + where to buy in {city}>"
  }},
  "notes": {{
    "porcje": "<servings — only if stated>",
    "czas_przygotowania": "<prep time — only if stated>",
    "czas_gotowania": "<cook time — only if stated>"
  }}
}}

Rules:
- ingredients_pl: one string per ingredient, fully in the target language; localise for {target_country}.
- ingredients_original: copy each ingredient line exactly as in the source.
- steps_pl: each step translated into the target language.
- tags: 3–5 short tags in the target language.
- substitutions: document substitutions (unavailable/brand → local equivalent). Omit universal ingredients.
- notes: include ONLY keys explicitly mentioned in the source. Omit the rest.
- If the input is not a recipe, extract what you can.

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
    source_lang = detect_language(raw_input, client)

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
                        city=target_city,
                        raw_input=raw_input,
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
