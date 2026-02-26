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

    # Translation settings
    source_language: Mapped[str] = mapped_column(String(10), default="he", nullable=False)
    source_country: Mapped[str] = mapped_column(String(10), default="IL", nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), default="pl", nullable=False)
    target_country: Mapped[str] = mapped_column(String(10), default="PL", nullable=False)
    target_city: Mapped[str] = mapped_column(String(100), default="Wrocław", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    recipes: Mapped[list["Recipe"]] = relationship("Recipe", back_populates="user")


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

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

    # Translation context snapshot (may differ from user defaults at time of creation)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    source_country: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_country: Mapped[str] = mapped_column(String(10), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="recipes")
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


class IngredientSubstitution(Base):
    __tablename__ = "ingredient_substitutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_country: Mapped[str] = mapped_column(String(10), nullable=False)
    target_country: Mapped[str] = mapped_column(String(10), nullable=False)
    substitution: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
