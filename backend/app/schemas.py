from datetime import datetime
from pydantic import BaseModel, EmailStr


# --- Auth ---

class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User ---

class UserSettings(BaseModel):
    source_language: str
    source_country: str
    target_language: str
    target_country: str
    target_city: str


class UserOut(BaseModel):
    id: int
    email: str
    source_language: str
    source_country: str
    target_language: str
    target_country: str
    target_city: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Recipe ---

class RecipeCreate(BaseModel):
    raw_input: str




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
    source_language: str
    source_country: str
    target_language: str
    target_country: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipeUserNotesUpdate(BaseModel):
    user_notes: str | None = None


class RecipeFavoriteUpdate(BaseModel):
    is_favorite: bool


# --- Ingredient Substitution ---

class IngredientSubstitutionOut(BaseModel):
    id: int
    ingredient_name: str
    source_country: str
    target_country: str
    substitution: str

    model_config = {"from_attributes": True}
