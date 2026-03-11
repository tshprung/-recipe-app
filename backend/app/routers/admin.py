import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _verify_admin_token(admin_token: str | None) -> None:
    expected = os.getenv("ADMIN_TOKEN") or ""
    if not expected or admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )


def _admin_token_dep(admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    _verify_admin_token(admin_token)


@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(
    db: Session = Depends(get_db),
    _: None = Depends(_admin_token_dep),
):
    """List all users (admin only)."""
    users = db.query(models.User).order_by(models.User.id).all()
    return [schemas.AdminUserOut.model_validate(u) for u in users]


@router.post("/upgrade-user")
def upgrade_user(
    payload: schemas.AdminUpgradeUserRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_admin_token_dep),
):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.transformations_limit = payload.new_limit
    if payload.transformations_used is not None:
        user.transformations_used = payload.transformations_used
    if payload.new_limit == -1:
        user.account_tier = "unlimited"
    elif payload.new_limit > 5:
        user.account_tier = "paid"
    else:
        user.account_tier = "free"

    db.commit()

    return {"detail": "User upgraded.", "email": user.email, "new_limit": user.transformations_limit}


@router.post("/users/{user_id}/block")
def block_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(_admin_token_dep),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_blocked = True
    db.commit()
    return {"detail": "User blocked.", "email": user.email}


@router.post("/users/{user_id}/unblock")
def unblock_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(_admin_token_dep),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_blocked = False
    db.commit()
    return {"detail": "User unblocked.", "email": user.email}


def _delete_user_cascade(user_id: int, db: Session) -> None:
    """Delete user and all related data (mirrors DELETE /users/me)."""
    db.query(models.ShoppingListRecipe).filter(models.ShoppingListRecipe.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(models.ShoppingListCache).filter(models.ShoppingListCache.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(models.Recipe).filter(models.Recipe.user_id == user_id).delete(synchronize_session=False)
    db.query(models.IngredientSubstitution).filter(
        models.IngredientSubstitution.created_by_user_id == user_id
    ).update({models.IngredientSubstitution.created_by_user_id: None})
    user = db.get(models.User, user_id)
    if user:
        db.delete(user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(_admin_token_dep),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _delete_user_cascade(user_id, db)
    db.commit()
    return {"detail": "User deleted.", "email": user.email}

