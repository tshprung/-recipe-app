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


@router.post("/upgrade-user")
def upgrade_user(
    payload: schemas.AdminUpgradeUserRequest,
    db: Session = Depends(get_db),
    admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
):
    _verify_admin_token(admin_token)

    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.transformations_limit = payload.new_limit
    if payload.new_limit == -1:
        user.account_tier = "unlimited"
    elif payload.new_limit > 5:
        user.account_tier = "paid"
    else:
        user.account_tier = "free"

    db.commit()

    return {"detail": "User upgraded.", "email": user.email, "new_limit": user.transformations_limit}

