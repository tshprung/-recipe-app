from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, model_validator


# --- Auth ---

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    captcha_token: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User ---

class UserSettings(BaseModel):
    target_language: str
    target_country: str
    target_city: str


class UserOut(BaseModel):
    id: int
    email: str
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
    variant_type: str  # "vegetarian" | "vegan" | "dairy_free" | "gluten_free" | "kosher"
    custom_instruction: str | None = None  # for user-chosen alternatives
    custom_title: str | None = None        # display title for the resulting variant tab


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


class SubstitutionReportRequest(BaseModel):
    original_label: str
    better_substitution: str
    source_country: str = "IL"
    target_country: str = "PL"


class AdminUpgradeUserRequest(BaseModel):
    email: EmailStr
    new_limit: int
