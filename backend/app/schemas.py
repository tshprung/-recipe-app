from __future__ import annotations

from datetime import datetime
from typing import Union

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


ALLOWED_ALLERGEN_CODES = {
    # EU/UK “top 14” allergens (stored as stable codes)
    "gluten_cereals",
    "crustaceans",
    "eggs",
    "fish",
    "peanuts",
    "soybeans",
    "milk",
    "tree_nuts",
    "celery",
    "mustard",
    "sesame",
    "sulphites",
    "lupin",
    "molluscs",
}


def sanitize_custom_allergens_text(text: str | None) -> str | None:
    """
    Best-effort sanitization for user-entered text that may later be shown in UI
    and used for best-effort filtering prompts.
    """
    if text is None:
        return None
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return None
    # Keep it short to avoid prompt abuse / accidental huge payloads.
    return cleaned[:500]


# --- Auth ---

class UserRegister(BaseModel):
    email: EmailStr
    password_hash: str = Field(min_length=1)
    captcha_token: str | None = None
    ui_language: str | None = "en"
    target_language: str
    target_country: str
    target_city: str
    target_zip: str | None = None
    dish_preferences: list[str] | None = None
    default_servings: int | None = None
    allergens: list[str] | None = None
    custom_allergens_text: str | None = None
    household_adults: int | None = None
    household_kids: int | None = None
    diet_filters: list[str] | None = None

    @field_validator("allergens")
    @classmethod
    def validate_register_allergens(cls, v: list[str] | None) -> list[str]:
        if v is None:
            return []
        cleaned: list[str] = []
        for raw in v:
            code = (raw or "").strip().lower()
            if not code or code in cleaned:
                continue
            if code not in ALLOWED_ALLERGEN_CODES:
                raise ValueError(f"Unknown allergen code: {code}")
            cleaned.append(code)
        return cleaned


class UserLogin(BaseModel):
    email: EmailStr
    password_hash: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Trial (anonymous try-for-free) ---

class TrialRecipeOut(BaseModel):
    id: int
    title: str
    ingredients: list[str]
    steps: list[str]
    author_name: str | None = None
    author_bio: str | None = None
    author_image_url: str | None = None
    image_url: str | None = None
    diet_tags: list[str] = Field(default_factory=list)


class TrialStartOut(BaseModel):
    trial_token: str
    country: str
    language: str
    recipes: list[TrialRecipeOut]
    remaining_actions: int


# --- Onboarding (guest pre-fetch + claim) ---

class OnboardingPrepareRequest(BaseModel):
    """Payload for pre-fetching starter recipes during onboarding (no auth)."""
    target_country: str = "PL"
    target_language: str = "en"
    target_city: str | None = None
    target_zip: str | None = None
    dish_preferences: list[str] = Field(default_factory=list)
    diet_filters: list[str] = Field(default_factory=list)
    default_servings: int = Field(default=4, ge=1, le=24)


class OnboardingPrepareResponse(BaseModel):
    claim_token: str


class OnboardingClaimRequest(BaseModel):
    """After sign-up: claim pre-fetched recipes and apply onboarding answers to user."""
    claim_token: str
    # Optional profile updates (from onboarding answers)
    ui_language: str | None = None
    target_language: str | None = None
    target_country: str | None = None
    target_city: str | None = None
    target_zip: str | None = None
    dish_preferences: list[str] | None = None
    household_adults: int | None = None
    household_kids: int | None = None
    diet_filters: list[str] | None = None
    default_servings: int | None = None
    allergens: list[str] | None = None
    custom_allergens_text: str | None = None


# --- User ---

class UserSettings(BaseModel):
    ui_language: str
    target_language: str
    target_country: str
    target_city: str
    target_zip: str | None = None
    dish_preferences: list[str] = Field(default_factory=list)
    household_adults: int | None = None
    household_kids: int | None = None
    diet_filters: list[str] = Field(default_factory=list)
    default_servings: int = Field(default=4, ge=1, le=24)
    allergens: list[str] = Field(default_factory=list)
    custom_allergens_text: str | None = None

    @field_validator("allergens")
    @classmethod
    def validate_allergens(cls, v: list[str]) -> list[str]:
        cleaned: list[str] = []
        for raw in v or []:
            code = (raw or "").strip().lower()
            if not code:
                continue
            if code not in ALLOWED_ALLERGEN_CODES:
                raise ValueError(f"Unknown allergen code: {code}")
            if code not in cleaned:
                cleaned.append(code)
        return cleaned

    @field_validator("custom_allergens_text")
    @classmethod
    def validate_custom_allergens_text(cls, v: str | None) -> str | None:
        return sanitize_custom_allergens_text(v)


class UserOut(BaseModel):
    id: int
    email: str
    ui_language: str
    target_language: str
    target_country: str
    target_city: str
    target_zip: str | None = None
    transformations_used: int
    transformations_limit: int
    is_verified: bool
    account_tier: str
    created_at: datetime
    is_admin: bool = False
    renewed_token: str | None = None  # set by backend on GET /users/me to slide expiry; client stores and does not put in user state
    dish_preferences: list[str] = Field(default_factory=list)
    household_adults: int | None = None
    household_kids: int | None = None
    diet_filters: list[str] = Field(default_factory=list)
    default_servings: int = 4
    allergens: list[str] = Field(default_factory=list)
    custom_allergens_text: str | None = None

    model_config = {"from_attributes": True}


# --- Recipe ---

class RecipeCreate(BaseModel):
    raw_input: str | None = None
    source_url: str | None = None

    @model_validator(mode="after")
    def require_raw_or_url(self):
        if (self.raw_input or "").strip() and (self.source_url or "").strip():
            raise ValueError("Provide either raw_input or source_url, not both")
        if not (self.raw_input or "").strip() and not (self.source_url or "").strip():
            raise ValueError("Provide either raw_input or source_url")
        return self




class RecipeOut(BaseModel):
    id: int
    user_id: int | None = None
    title_pl: str
    title_original: str
    ingredients_pl: list
    ingredients_original: list
    steps_pl: list
    tags: list
    substitutions: dict
    notes: dict
    user_notes: str | None
    is_favorite: bool
    raw_input: str
    detected_language: str | None
    target_language: str
    target_country: str
    target_city: str
    created_at: datetime
    author_name: str | None = None
    author_bio: str | None = None
    author_image_url: str | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    user_rating: int | None = None
    diet_tags: list[str] = Field(default_factory=list)
    image_url: str | None = None

    model_config = {"from_attributes": True}


class RecipeMetaUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    prep_time_minutes: int | None = Field(default=None, ge=0, le=24 * 60)
    cook_time_minutes: int | None = Field(default=None, ge=0, le=24 * 60)


class RecipeUserNotesUpdate(BaseModel):
    user_notes: str | None = None


class RecipeFavoriteUpdate(BaseModel):
    is_favorite: bool


# --- Shopping List ---

class ShoppingListAddRequest(BaseModel):
    recipe_id: int


class ShoppingListRecipeIdsOut(BaseModel):
    recipe_ids: list[int]


class ShoppingListOut(BaseModel):
    recipe_ids: list[int]
    items: dict  # {"Warzywa i owoce": [...], "Nabiał": [...], ...}


# --- Ingredient Substitution ---

class IngredientSubstitutionOut(BaseModel):
    id: int
    ingredient_name: str
    source_country: str
    target_country: str
    substitution: str

    model_config = {"from_attributes": True}


# --- Recipe Adaptations ---

class AdaptRequest(BaseModel):
    variant_type: str | None = None   # single type (legacy)
    variant_types: list[str] | None = None  # multiple types applied in order (e.g. ["vegetarian", "kosher"])
    custom_instruction: str | None = None  # for user-chosen alternatives
    custom_title: str | None = None        # display title for the resulting variant tab

    @model_validator(mode="after")
    def require_variant_type_or_types(self):
        has_single = self.variant_type is not None
        has_multi = bool(self.variant_types)
        if has_single and not has_multi:
            return self
        if has_multi and not has_single:
            return self
        raise ValueError("Provide either variant_type or variant_types (not both)")


class RecipeVariantOut(BaseModel):
    id: int
    recipe_id: int
    variant_type: str
    title_pl: str
    ingredients_pl: list
    steps_pl: list
    notes: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class DeleteVariantRequest(BaseModel):
    variant_type: str  # e.g. "vegetarian" or "vegetarian,kosher"


class IngredientAlternativesRequest(BaseModel):
    ingredient: str  # the ingredient line or name to find alternatives for
    diet_filters: list[str] | None = None  # e.g. ["vegan", "dairy_free"]; empty = no diet filter


class WhatCanIMakeRequest(BaseModel):
    ingredients: list[str]  # ingredients the user has
    diet_filters: list[str] | None = None  # e.g. ["vegetarian", "vegan", "dairy_free"]
    assume_pantry: bool = True  # assume salt, sugar, oil, etc.
    source: str = "my_recipes"  # "my_recipes" | "ai"


class WhatCanIMakeMatchOut(BaseModel):
    recipe: RecipeOut
    can_make: bool
    missing_ingredients: list[str]


class WhatCanIMakeMyRecipesOut(BaseModel):
    source: str = "my_recipes"
    matches: list[WhatCanIMakeMatchOut]


class AISuggestedRecipeOut(BaseModel):
    title: str
    ingredients: list[str]
    steps: list[str]
    missing_ingredients: list[str] | None = None


class WhatCanIMakeAIOut(BaseModel):
    source: str = "ai"
    suggestions: list[AISuggestedRecipeOut]


class FromAISuggestionRequest(BaseModel):
    """Create a recipe from an AI suggestion without calling translation (no extra credit)."""
    title: str
    ingredients: list[str]  # e.g. ["2 cups flour", "1 egg"]
    steps: list[str]


class WhatCanIMakeIngredientAlternativesRequest(BaseModel):
    previous_ingredients: list[str]  # original list
    added_ingredients: list[str]  # user marked "I have this"


class IngredientAlternativeOut(BaseModel):
    name: str
    notes: str | None = None


class IngredientAlternativesOut(BaseModel):
    alternatives: list[IngredientAlternativeOut]


class ReplaceIngredientRequest(BaseModel):
    variant_type: str | None = None  # null/omitted = original recipe
    ingredient_index: int = Field(ge=0)
    new_ingredient: str = Field(min_length=1)


class SubstitutionReportRequest(BaseModel):
    original_label: str
    better_substitution: str
    source_country: str = "IL"
    target_country: str = "PL"


class AdminUserOut(BaseModel):
    id: int
    email: str
    transformations_used: int
    transformations_limit: int
    account_tier: str
    is_verified: bool
    is_blocked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUpgradeUserRequest(BaseModel):
    email: EmailStr
    new_limit: int
    transformations_used: int | None = None  # optional reset of used count


class AdminTrialIpWhitelistIn(BaseModel):
    ip_address: str
    label: str | None = None


class AdminTrialIpWhitelistOut(BaseModel):
    id: int
    ip_address: str
    label: str | None = None

    model_config = {"from_attributes": True}
