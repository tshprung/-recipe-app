import json
import os

from openai import APIError, OpenAI, RateLimitError

SYSTEM_PROMPT = (
    "You are a professional recipe translator specialising in Hebrew → Polish translation. "
    "You have deep knowledge of Israeli cuisine, Polish supermarkets (Biedronka, Lidl, Kaufland, "
    "Carrefour, local bazaars), and how to adapt Middle-Eastern recipes for a Polish home cook. "
    "Your most important job is ingredient localisation: every ingredient in the Polish output "
    "MUST be something a home cook can buy in a Polish supermarket. "
    "Israeli brand names (Osem, Telma, Elite, Tnuva, Yacobs, Strauss, Tara, and all others) must NEVER "
    "appear anywhere in the output — replace every brand with the generic Polish product name. "
    "If you are unsure whether an ingredient is available in Polish supermarkets, substitute it or flag it — "
    "never leave an uncertain or Israeli-specific item unchanged. "
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
  LOCALISATION IS MANDATORY — apply these rules to every ingredient before writing it:
  1. Israeli brand names — ZERO TOLERANCE. Brands such as Osem, Telma, Elite, Tnuva, Yacobs,
     Strauss, Tara, Angel Bakeries, or any other Israeli brand MUST NEVER appear anywhere in the
     output. Always replace with the generic Polish product name.
  2. Sheep/goat feta or any Israeli white cheese (גבינה לבנה, גבינת צאן, etc.) → "ser feta"
     (available in every Polish supermarket; no further note needed).
  3. Products unavailable in Polish supermarkets → replace with the closest widely-available Polish
     equivalent. When in doubt whether something is available in Poland, substitute it or flag it
     in the substitutions field — never leave an uncertain ingredient as-is.
  4. Default rule: if an ingredient sounds Israeli-specific or you are not confident a Polish shopper
     can find it in a standard supermarket, find the Polish supermarket equivalent.
  5. Middle-Eastern staples that DO exist in Poland (tahini, za'atar, ras el hanout, harissa, sumac,
     halva, date syrup, pomegranate molasses, labneh, bulgur, freekeh, etc.) → keep them by their
     Polish/international name; they are sold in Biedronka, Lidl, or ethnic shops.
  6. Never write an ingredient in ingredients_pl that a Polish shopper cannot buy. If there is truly
     no equivalent, describe what it is generically (e.g. "ser biały kremowy" instead of a brand).
- ingredients_original: copy each ingredient line exactly as it appears in the Hebrew.
- steps_pl: each cooking step as a separate string, translated fully into Polish.
  In the steps, also replace any brand names or unavailable items with their Polish equivalents.
- tags: 3–5 short Polish tags (e.g. "wegetariański", "kuchnia bliskowschodnia", "szybkie", "bez glutenu").
- substitutions: document every substitution you made (Israeli/unavailable → Polish equivalent),
  including where to find it in {city}. Omit only truly universal ingredients (eggs, flour, oil, salt, sugar).
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

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
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
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {e}") from e
