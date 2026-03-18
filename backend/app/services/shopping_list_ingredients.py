"""
Normalize and aggregate recipe ingredients for shopping list display.

- Strip cooking instructions from names (e.g. "beaten", "soaked in water and squeezed").
- Convert "X for coating" to "some X".
- Merge same ingredient and sum quantities (e.g. "1/2 tablespoon salt" + "1/2 tablespoon salt" → "1 tablespoon salt").
"""

import re
from collections import defaultdict

# Phrases that describe cooking/prep and should be removed from shopping list names
COOKING_PHRASES = [
    r",\s*beaten\s*$",
    r",\s*lightly\s+beaten\s*$",
    r",\s*soaked\s+in\s+water\s+and\s+squeezed\s*$",
    r"\s+soaked\s+in\s+water\s+and\s+squeezed\s*$",
    r",\s*soaked\s+in\s+water\s*$",
    r",\s*diced\s*$",
    r",\s*minced\s*$",
    r",\s*chopped\s*$",
    r",\s*finely\s+chopped\s*$",
    r",\s*sliced\s*$",
    r",\s*peeled\s+and\s+chopped\s*$",
    r",\s*peeled\s*$",
    r",\s*grated\s*$",
    r",\s*at\s+room\s+temperature\s*$",
    r",\s*softened\s*$",
    r",\s*melted\s*$",
    r"\s+melted\s*$",
    r"^\s*melted\s+",
    r",\s*cooked\s*$",
    r"\s+cooked\s*$",
    r"^\s*cooked\s+",
    r",\s*cut\s*$",
    r"\s+cut\s*$",
    r"^\s*cut\s+",
    r"\s+for\s+coating\s*$",
    r",\s*for\s+coating\s*$",
    # "for sauce", "for shallow frying", etc. — usage, not buying info
    r",\s*for\s+[\w\s]+\s*$",
    r"\s+for\s+[\w\s]+\s*$",
    # Prep parentheticals (do not strip "(local name, Language)" — that has comma and language word)
    r",\s*chopped\s*\(minus\s+a\s+handful\)\s*$",
    r",\s*\(minus\s+a\s+handful\)\s*$",
    r"\s*\(minus\s+a\s+handful\)\s*$",
    r",\s*\(to\s+taste\)\s*$",
    r"\s*\(to\s+taste\)\s*$",
    r",\s*\(optional\)\s*$",
    r"\s*\(optional\)\s*$",
]

# When the name part is entirely one of these (e.g. after splitting on comma), treat as empty
COOKING_PHRASES_FULL = [
    r"^\s*beaten\s*$",
    r"^\s*lightly\s+beaten\s*$",
    r"^\s*soaked\s+in\s+water\s+and\s+squeezed\s*$",
    r"^\s*soaked\s+in\s+water\s*$",
]

COOKING_PATTERNS = [re.compile(p, re.IGNORECASE) for p in COOKING_PHRASES]
COOKING_PATTERNS_FULL = [re.compile(p, re.IGNORECASE) for p in COOKING_PHRASES_FULL]

# Phrases that are not real shopping items (multilingual)
_EXCLUDE_ITEM_PATTERNS = [
    # English
    r"^\s*season(?:ing)?\s+to\s+taste\s*$",
    r"^\s*season\s+to\s+taste\s*$",
    # Hebrew
    r"^\s*תיבול\s+לפי\s+טעם\s*$",
    r"^\s*תיבול\s+לפי\s+הטעם\s*$",
    r"^\s*תבלון\s+לפי\s+טעם\s*$",
]
EXCLUDE_ITEM_PATTERNS = [re.compile(p) for p in _EXCLUDE_ITEM_PATTERNS]

# Hebrew prep words to strip from ingredient names (keep "ground"/טחון)
_HE_PREP_SUFFIXES = {
    "קצוץ", "קצוצה", "קצוצים", "קצוצות",
    "חתוך", "חתוכה", "חתוכים", "חתוכות",
    "פרוס", "פרוסה", "פרוסים", "פרוסות",
    "קלוף", "קלופה", "קלופים", "קלופות",
    "מבושל", "מבושלת", "מבושלים", "מבושלות",
    "צלוי", "צלויה", "צלויים", "צלויות",
    "מטוגן", "מטוגנת", "מטוגנים", "מטוגנות",
    "אפוי", "אפויה", "אפויים", "אפויות",
}
_HE_GROUND_WORDS = {"טחון", "טחונה", "טחונים", "טחונות"}


def _strip_hebrew_prep(name: str) -> str:
    s = (name or "").strip()
    if not s:
        return s
    words = s.split()
    # Strip trailing prep words, but never strip "ground" (טחון)
    while words:
        w = words[-1].strip("()[]{}.,;:!?'\"׳״")
        if not w:
            words.pop()
            continue
        if w in _HE_GROUND_WORDS:
            break
        if w in _HE_PREP_SUFFIXES:
            words.pop()
            continue
        break
    return " ".join(words).strip()


def _should_exclude_item(label: str) -> bool:
    s = (label or "").strip()
    if not s:
        return True
    for pat in EXCLUDE_ITEM_PATTERNS:
        if pat.match(s):
            return True
    return False

# Units we recognize for quantity aggregation (same unit + same name → sum)
VOLUME_UNITS = {
    "tablespoon", "tablespoons", "tbsp", "tb",
    "teaspoon", "teaspoons", "tsp",
    "cup", "cups",
}
VOLUME_WEIGHT_UNITS = VOLUME_UNITS | {
    "g", "gram", "grams", "kg",
    "ml", "milliliter", "milliliters", "l", "liter", "liters",
}
COUNTABLE_UNITS = {
    "egg", "eggs",
    "slice", "slices",
    "clove", "cloves",
    "piece", "pieces",
    "sprig", "sprigs",
    "pinch", "pinches",
}
KNOWN_UNITS = VOLUME_WEIGHT_UNITS | COUNTABLE_UNITS

# A small set of common countable nouns that should pluralize when unit is empty.
# This avoids "8 carrot" while not trying to pluralize everything (e.g. "rice", "salt").
_COUNTABLE_NOUNS = {
    "onion", "tomato", "potato", "pepper", "cucumber", "carrot",
    "apple", "banana", "lemon", "lime", "avocado",
}

# Convert tbsp/tsp to tablespoons for aggregation (1 tbsp = 3 tsp). Cups stay separate.
TABLESPOON_TSP_TO_TABLESPOONS = {
    "tablespoon": 1, "tablespoons": 1, "tbsp": 1, "tb": 1,
    "teaspoon": 1 / 3, "teaspoons": 1 / 3, "tsp": 1 / 3,
}

# Minimum volume for tbsp/tsp display (avoid "0 tablespoons")
MIN_TABLESPOONS = 1 / 3  # 1 teaspoon

# Oil-like names merged under one key; round up to at least 1 cup when in volume
OIL_NAME_KEY = "oil"
OIL_NAMES = {"oil", "olive oil", "vegetable oil", "cooking oil", "sunflower oil", "canola oil", "rapeseed oil"}
MIN_OIL_CUPS = 1.0

# Adjectives to strip for aggregation so "2 medium onions" + "1 onion" → "3 onions"
SIZE_ADJECTIVES = {"medium", "large", "small", "ripe", "fresh", "whole", "big", "little"}


def strip_cooking_instructions(name: str) -> str:
    """Remove cooking/prep phrases from ingredient name for shopping list."""
    if not name or not isinstance(name, str):
        return (name or "").strip()
    result = name.strip()
    for pat in COOKING_PATTERNS_FULL:
        if pat.match(result):
            return ""
    for pat in COOKING_PATTERNS:
        result = pat.sub("", result)
    result = result.strip().rstrip(",").strip()
    result = _strip_hebrew_prep(result)
    return result.strip()


def _normalize_amount_range(amount: str) -> str:
    """'1 to 1.25 cups' or '1-1.25' → '1.25 cups' or '1.25' (use upper bound for shopping)."""
    if not amount:
        return amount
    amount = amount.strip()
    # "1 to 1.25" or "1 to 1.25 cups" or "1 - 1.25"
    m = re.match(r"^([\d./\s]+)\s+(?:to|-|–)\s+([\d./]+)\s*(.*)$", amount, re.IGNORECASE)
    if m:
        rest = m.group(3).strip()
        return f"{m.group(2).strip()} {rest}".strip() if rest else m.group(2).strip()
    return amount


def _extract_weight_from_parenthetical(amount: str, name: str) -> tuple[str, str]:
    """If amount or name contains '(N g)' or '(N grams)', use that as amount. E.g. '3 tablespoons (45 grams)' + 'melted butter' → ('45 grams', 'melted butter')."""
    combined = f"{amount} {name}"
    match = re.search(r"\((\d+(?:\.\d+)?)\s*(g|grams?)\s*\)", combined, re.IGNORECASE)
    if not match:
        return amount, name
    num, u = match.group(1), match.group(2).lower()
    weight = f"{num} g" if u == "g" else f"{num} grams"
    new_amount = re.sub(r"\s*\(\d+(?:\.\d+)?\s*(?:g|grams?)\s*\)\s*", " ", amount, flags=re.IGNORECASE).strip()
    new_name = re.sub(r"\s*\(\d+(?:\.\d+)?\s*(?:g|grams?)\s*\)\s*", " ", name, flags=re.IGNORECASE).strip()
    # Prefer weight when we found it (use it as amount and drop the volume part)
    return weight, new_name


# Common singulars so "onions" + "onion" merge
_SINGULAR_PLURAL: dict[str, str] = {
    "onions": "onion", "tomatoes": "tomato", "potatoes": "potato", "peppers": "pepper",
    "cucumbers": "cucumber", "carrots": "carrot", "apples": "apple", "eggs": "egg",
    "cloves": "clove", "sprigs": "sprig", "pieces": "piece", "slices": "slice",
    "lemons": "lemon", "limes": "lime", "garlic": "garlic",
}


def _normalize_name_for_aggregation(name_rest: str, unit: str) -> str:
    """Canonical name for merging: strip size adjectives, merge oil names, singularize countables."""
    name = (name_rest or "").strip().lower()
    if not name:
        return (unit or "").strip().lower() or ""
    # Merge oil variants into one key
    if name in OIL_NAMES:
        return OIL_NAME_KEY
    for oil in OIL_NAMES:
        if name.endswith(" " + oil) or name == oil:
            return OIL_NAME_KEY
    # Strip leading size adjectives: "medium onions" → "onions", "ripe tomatoes" → "tomatoes"
    words = name.split()
    while words and words[0] in SIZE_ADJECTIVES:
        words.pop(0)
    name = " ".join(words) if words else name
    # Singularize for key so "onions" and "onion" merge
    if name in _SINGULAR_PLURAL:
        return _SINGULAR_PLURAL[name]
    if name.endswith("s") and not name.endswith("ss") and len(name) > 2:
        singular = name[:-1]
        if singular in _SINGULAR_PLURAL.values():
            return singular
    return name


def normalize_ingredient_for_shopping(amount: str, name: str) -> tuple[str, str]:
    """
    Normalize (amount, name) for shopping: strip cooking instructions,
    convert 'for coating' to estimated amount 'some', "X to Y" → Y (upper bound),
    and prefer weight in parentheses e.g. "3 tbsp (45 g)" → "45 grams".
    Returns (amount, normalized_name).
    """
    raw_name = (name or "").strip()
    amount = (amount or "").strip()
    amount = _normalize_amount_range(amount)
    amount, raw_name = _extract_weight_from_parenthetical(amount, raw_name)
    had_for_coating = bool(re.search(r"for\s+coating", raw_name + " " + (amount or ""), re.IGNORECASE))

    name = strip_cooking_instructions(raw_name)

    # "flour for coating" → "some flour"
    if had_for_coating and (not amount or re.match(r"^(some|a\s+little|as\s+needed|for\s+coating)$", amount, re.IGNORECASE)):
        amount = "some"

    return (amount, name)


def _parse_fraction(s: str) -> float | None:
    """Parse '1/2', '1/4', '2/3' etc. Return None if not a fraction."""
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", s.strip())
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        return num / den if den else None
    return None


def _parse_number(s: str) -> float | None:
    """Parse '1', '2.5', '1/2'. Return None if not a number."""
    s = s.strip()
    frac = _parse_fraction(s)
    if frac is not None:
        return frac
    try:
        return float(s)
    except ValueError:
        return None


def _tokenize_amount_and_rest(label: str) -> tuple[float | None, str, str]:
    """
    Split '1/2 tablespoon salt' or '1 egg' into (numeric_value, unit_or_countable, name_rest).
    Returns (value, unit, rest) where rest is the rest of the string after amount+unit.
    If value cannot be parsed, returns (None, '', label).
    """
    rest = label.strip()
    if not rest:
        return (None, "", "")

    tokens = rest.split()
    if not tokens:
        return (None, "", rest)

    value = _parse_number(tokens[0])
    if value is None:
        return (None, "", rest)

    # One token: "1" or "1/2" → no unit, rest is empty (whole string is amount?)
    if len(tokens) == 1:
        return (value, "", "")

    second = tokens[1].lower().rstrip("s")
    second_plural = tokens[1].lower()

    # Second token is a known unit
    if second in KNOWN_UNITS or second_plural in KNOWN_UNITS:
        unit = tokens[1].lower()
        name_rest = " ".join(tokens[2:]).strip()
        # "1 egg" → unit "egg", name_rest "" → we'll use unit as name
        if not name_rest and unit in COUNTABLE_UNITS:
            name_rest = unit  # so key is (unit, name) = ("", "egg") for grouping
            unit_for_key = ""
        elif not name_rest:
            name_rest = unit
            unit_for_key = ""
        else:
            unit_for_key = unit
        return (value, unit_for_key, name_rest)

    # No known unit: "1 onion" → value 1, unit "", name "onion"
    return (value, "", " ".join(tokens[1:]).strip())


def _tablespoon_or_teaspoon_to_tablespoons(value: float, unit: str) -> float | None:
    """Convert tbsp/tsp to tablespoons for merging. Returns None for cup or other units."""
    u = (unit or "").strip().lower()
    if u in TABLESPOON_TSP_TO_TABLESPOONS:
        return value * TABLESPOON_TSP_TO_TABLESPOONS[u]
    return None


def _aggregation_key(unit: str, name_rest: str) -> tuple[str, str]:
    """Key for grouping: (unit, normalized_name)."""
    name = (name_rest or "").strip() or unit
    return (unit.strip().lower(), name.strip().lower())


def _is_plain_water(label: str) -> bool:
    """True if this ingredient is plain water (exclude from shopping list). Keeps special waters (sparkling, coconut, mineral, etc.)."""
    label = (label or "").strip()
    if not label:
        return False
    if label.lower() == "water":
        return True
    value, unit, name_rest = _tokenize_amount_and_rest(label)
    name = ((name_rest or "").strip() or (unit or "").strip()).lower()
    return name == "water"


def _format_quantity(value: float, unit: str, name_rest: str) -> str:
    """Format (value, unit, name_rest) back to a single ingredient string."""
    name = (name_rest or "").strip() or unit
    if not name:
        return ""

    # Pretty-print fraction or decimal
    if value == int(value) and value >= 0:
        num_str = str(int(value))
    elif value == 0.5:
        num_str = "1/2"
    elif value == 0.25:
        num_str = "1/4"
    elif value == 0.75:
        num_str = "3/4"
    elif value == int(value):
        num_str = str(int(value))
    else:
        num_str = str(round(value, 2)).rstrip("0").rstrip(".")

    if unit:
        # Pluralize volume units (tablespoon → tablespoons when value != 1)
        display_unit = unit
        if unit in VOLUME_UNITS and value != 1:
            display_unit = unit + "s" if not unit.endswith("s") else unit
        part = f"{num_str} {display_unit}"
        if name and name != unit:
            part += f" {name}"
        return part
    # Countable: "2 eggs" vs "1 egg"
    if value != 1 and name in COUNTABLE_UNITS:
        plural = name + "s" if not name.endswith("s") else name
        return f"{num_str} {plural}"
    # Heuristic pluralization when unit is empty (English only, common produce nouns)
    if not unit and value != 1 and name in _COUNTABLE_NOUNS and not name.endswith("s"):
        return f"{num_str} {name}s"
    return f"{num_str} {name}"


def aggregate_ingredients(ingredient_labels: list[str]) -> list[str]:
    """
    Merge same ingredient and sum quantities.
    E.g. ["1 egg", "1 egg", "1/2 tablespoon salt", "1/2 tablespoon salt"]
    → ["2 eggs", "1 tablespoon salt"].
    Volume units (tbsp + tsp) are converted and merged; minimum 1 tsp for spices.
    Oil is merged and rounded up to at least 1 cup. "2 medium onions" + "1 onion" → "3 onions".
    """
    volume_groups: dict[str, list[float]] = defaultdict(list)
    other_groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    unparseable: list[str] = []

    for label in ingredient_labels:
        value, unit, name_rest = _tokenize_amount_and_rest(label)
        if value is None:
            unparseable.append(label)
            continue
        raw_name = ((name_rest or "").strip() or (unit or "").strip()).lower()
        if not raw_name:
            unparseable.append(label)
            continue
        name_key = _normalize_name_for_aggregation(raw_name, unit)

        tbsp = _tablespoon_or_teaspoon_to_tablespoons(value, unit) if unit else None
        if tbsp is not None:
            volume_groups[name_key].append(tbsp)
        else:
            key = (unit.strip().lower(), name_key)
            if not key[1]:
                key = (key[0], raw_name)
            other_groups[key].append(value)

    out: list[str] = []
    for name_key, values in volume_groups.items():
        total_tbsp = sum(values)
        if total_tbsp < MIN_TABLESPOONS:
            total_tbsp = MIN_TABLESPOONS
        if name_key == OIL_NAME_KEY and total_tbsp < MIN_OIL_CUPS * 16:
            total_tbsp = MIN_OIL_CUPS * 16
        total_tbsp = round(total_tbsp * 4) / 4
        out.append(_format_quantity(total_tbsp, "tablespoon", name_key))

    for (unit, name), values in other_groups.items():
        total = sum(values)
        if name == OIL_NAME_KEY and unit in ("cup", "cups") and total < MIN_OIL_CUPS:
            total = MIN_OIL_CUPS
        name_display = name
        if name in _SINGULAR_PLURAL.values() and total != 1:
            plural = next((p for p, s in _SINGULAR_PLURAL.items() if s == name), name + "s")
            name_display = plural
        out.append(_format_quantity(total, unit, name_display))

    out.extend(unparseable)
    # Exclude plain water (tap water); keep special waters e.g. sparkling, coconut, mineral
    out = [x for x in out if x and not _is_plain_water(x) and not _should_exclude_item(x)]
    return out


def normalize_and_aggregate(ingredient_labels: list[str]) -> list[str]:
    """
    First normalize each label (strip cooking instructions) then aggregate.
    Use this when you already have full "amount name" strings (e.g. after substitution).
    """
    # Normalization of full string: we need to strip cooking from the name part.
    # Labels are "amount name" so we need to split once and normalize name.
    normalized: list[str] = []
    for s in ingredient_labels:
        s = (s or "").strip()
        if not s:
            continue
        # Heuristic: last part after comma is often cooking (e.g. "1 egg, beaten")
        # We already have strip_cooking_instructions; apply to the whole string
        # by treating "amount name" where name may have ", beaten" etc.
        parts = s.split(",", 1)
        if len(parts) == 2:
            amount_part = parts[0].strip()
            name_part = parts[1].strip()
            name_clean = strip_cooking_instructions(name_part)
            if name_clean:
                s = f"{amount_part}, {name_clean}"
            else:
                s = amount_part
        # Also strip from the right part of "amount name" when there's no comma
        # e.g. "1/2 slice white bread soaked in water and squeezed"
        for pat in COOKING_PATTERNS:
            s = pat.sub("", s)
        s = s.strip().rstrip(",").strip()
        if s:
            normalized.append(s)

    return aggregate_ingredients(normalized)
