"""Suggest ingredient alternatives for a given diet context (e.g. vegan, dairy-free)."""
import json
import os

from openai import APIError, OpenAI, RateLimitError

SYSTEM_PROMPT = (
    "You suggest ingredient alternatives for cooking. "
    "Given an ingredient and optional diet restrictions, return 3–6 substitute options. "
    "Respond with valid JSON only: {\"alternatives\": [{\"name\": \"...\", \"notes\": \"...\"}, ...]}. "
    "Keep names concise; use notes for where to buy or how to use."
)

USER_PROMPT_TEMPLATE = """\
Ingredient: {ingredient}

Diet restrictions (apply only these; if empty, suggest general alternatives): {diet_list}

Return JSON:
{{
  "alternatives": [
    {{ "name": "<substitute name>", "notes": "<optional short note>" }},
    ...
  ]
}}
"""


def get_ingredient_alternatives(
    ingredient: str,
    diet_filters: list[str] | None = None,
    target_language: str = "en",
) -> list[dict]:
    """
    Return list of dicts with keys name, notes (notes optional).
    Uses OpenAI; raises RuntimeError if no API key or on rate limit.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")

    diet_list = ", ".join(diet_filters) if diet_filters else "none"
    prompt = USER_PROMPT_TEMPLATE.format(
        ingredient=(ingredient or "").strip() or "unknown",
        diet_list=diet_list,
    )
    # Ask for output in target language
    if target_language and target_language.strip().lower() != "en":
        prompt += f"\nWrite all alternative names and notes in the user's language (code: {target_language.strip().lower()})."

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
            temperature=0.3,
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
    alternatives = data.get("alternatives") or []
    return [
        {"name": str(a.get("name", "")).strip(), "notes": (a.get("notes") or "").strip() or None}
        for a in alternatives
        if isinstance(a, dict) and a.get("name")
    ]
