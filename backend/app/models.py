from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Quota & verification
    transformations_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transformations_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_token_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    account_tier: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    starter_recipes_added: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Cooking preferences
    dish_preferences: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # e.g. ["pasta", "soups", "chicken"]
    household_adults: Mapped[int | None] = mapped_column(Integer, nullable=True)
    household_kids: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diet_filters: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # e.g. ["vegetarian", "vegan"]
    default_servings: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    allergens: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    custom_allergens_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Login security
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lockout_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Translation settings (target only; source is auto-detected per recipe)
    ui_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), default="pl", nullable=False)
    target_country: Mapped[str] = mapped_column(String(10), default="PL", nullable=False)
    target_city: Mapped[str] = mapped_column(String(100), default="Wrocław", nullable=False)
    target_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    recipes: Mapped[list["Recipe"]] = relationship("Recipe", back_populates="user")


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    trial_session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("trial_sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )

    title_pl: Mapped[str] = mapped_column(String(500), nullable=False)
    title_original: Mapped[str] = mapped_column(String(500), nullable=False)

    # JSON fields
    ingredients_pl: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ingredients_original: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    steps_pl: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    substitutions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional author attribution (e.g. for starter recipes from famous cooks)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Diet compliance tags (e.g. ["kosher"] for starter recipes created with that diet)
    diet_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Times + rating (user-owned)
    prep_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cook_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Recipe photo (dish image); filled by image service (cache or generate)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Target locale snapshot; source language is auto-detected
    detected_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_country: Mapped[str] = mapped_column(String(10), nullable=False)
    target_city: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User | None"] = relationship("User", back_populates="recipes")
    trial_session: Mapped["TrialSession | None"] = relationship(
        "TrialSession", back_populates="recipes"
    )
    variants: Mapped[list["RecipeVariant"]] = relationship(
        "RecipeVariant", back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeVariant(Base):
    __tablename__ = "recipe_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title_pl: Mapped[str] = mapped_column(String(500), nullable=False)
    ingredients_pl: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    steps_pl: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="variants")


class ShoppingListRecipe(Base):
    __tablename__ = "shopping_list_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User")
    recipe: Mapped["Recipe"] = relationship("Recipe")


class ShoppingListCache(Base):
    """Cached categorized shopping list per user, keyed by sorted recipe_ids."""

    __tablename__ = "shopping_list_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipe_ids_snapshot: Mapped[list] = mapped_column(JSON, nullable=False)  # sorted list of recipe ids
    items: Mapped[dict] = mapped_column(JSON, nullable=False)  # categorized dict
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PreparedStarterRecipes(Base):
    """Temporary storage for pre-fetched starter recipes during onboarding (claim by token)."""

    __tablename__ = "prepared_starter_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    recipes_data: Mapped[list] = mapped_column(JSON, nullable=False)  # list of recipe dicts
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecipeImageCache(Base):
    """Cache of recipe dish images by normalized title (and optional language). Reuse same image for multiple recipes."""

    __tablename__ = "recipe_image_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TrialSession(Base):
    """Anonymous trial session: 5 actions per token_id, IP-limited."""

    __tablename__ = "trial_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    used_actions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    recipes: Mapped[list["Recipe"]] = relationship(
        "Recipe", back_populates="trial_session", cascade="all, delete-orphan"
    )


class TrialIpWhitelist(Base):
    """IP addresses exempt from trial per-IP limits (admin-managed)."""

    __tablename__ = "trial_ip_whitelist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)


class IngredientSubstitution(Base):
    __tablename__ = "ingredient_substitutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_country: Mapped[str] = mapped_column(String(10), nullable=False)
    target_country: Mapped[str] = mapped_column(String(10), nullable=False)
    substitution: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
