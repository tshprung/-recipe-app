"""Single place for deleting a user and all related data. Used by DELETE /users/me and admin delete user."""

from sqlalchemy.orm import Session

from .. import models


def delete_user_and_data(user_id: int, db: Session) -> None:
    """Delete user and all data owned by or referencing them. Caller must commit."""
    # Shopping list entries
    db.query(models.ShoppingListRecipe).filter(models.ShoppingListRecipe.user_id == user_id).delete(
        synchronize_session=False
    )
    # Shopping list cache
    db.query(models.ShoppingListCache).filter(models.ShoppingListCache.user_id == user_id).delete(
        synchronize_session=False
    )
    # Recipes (RecipeVariant cascades via relationship)
    db.query(models.Recipe).filter(models.Recipe.user_id == user_id).delete(synchronize_session=False)
    # Unlink ingredient substitutions created by this user
    db.query(models.IngredientSubstitution).filter(
        models.IngredientSubstitution.created_by_user_id == user_id
    ).update({models.IngredientSubstitution.created_by_user_id: None})
    # User
    user = db.get(models.User, user_id)
    if user:
        db.delete(user)
