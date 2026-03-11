import os

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])


def _admin_emails() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS") or ""
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    data = schemas.UserOut.model_validate(current_user).model_dump()
    data["is_admin"] = (current_user.email or "").strip().lower() in _admin_emails()
    return schemas.UserOut(**data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete the current user and all their data (recipes, shopping list entries)."""
    user_id = current_user.id

    # 1. Remove user's shopping list entries
    db.query(models.ShoppingListRecipe).filter(models.ShoppingListRecipe.user_id == user_id).delete()

    # 2. Delete user's recipes (RecipeVariant cascades via relationship)
    db.query(models.Recipe).filter(models.Recipe.user_id == user_id).delete()

    # 3. Unlink ingredient substitutions created by this user
    db.query(models.IngredientSubstitution).filter(
        models.IngredientSubstitution.created_by_user_id == user_id
    ).update({models.IngredientSubstitution.created_by_user_id: None})

    # 4. Delete the user
    db.delete(current_user)
    db.commit()
    return None


@router.patch("/me/settings", response_model=schemas.UserOut)
def update_settings(
    payload: schemas.UserSettings,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    for field, value in payload.model_dump().items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
