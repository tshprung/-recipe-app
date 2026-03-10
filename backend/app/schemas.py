from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, model_validator


# --- Auth ---

class UserRegister(BaseModel):
    email: EmailStr
    password_hash: str = Field(min_length=1)
    captcha_token: str | None = None
    ui_language: str | None = "en"
    target_language: str
    target_country: str
    target_city: str


class UserLogin(BaseModel):
    email: EmailStr
    password_hash: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User ---

class UserSettings(BaseModel):
    ui_language: str
    target_language: str
    target_country: str
    target_city: str


class UserOut(BaseModel):
    id: int
    email: str
    ui_language: str
    target_language: str
    target_country: str
    target_city: str
    transformations_used: int
    transformations_limit: int
    is_verified: bool
    account_tier: str
    created_at: datetime

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
    user_id: int
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

    model_config = {"from_attributes": True}


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


class SubstitutionReportRequest(BaseModel):
    original_label: str
    better_substitution: str
    source_country: str = "IL"
    target_country: str = "PL"


class AdminUpgradeUserRequest(BaseModel):
    email: EmailStr
    new_limit: int
