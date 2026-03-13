import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user_optional
from ..database import get_db
from ..services.user_deletion import delete_user_and_data

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _admin_emails() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS") or ""
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def _verify_admin_token(admin_token: str | None) -> bool:
    expected = os.getenv("ADMIN_TOKEN") or ""
    return bool(expected and admin_token == expected)


def _require_admin(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    current_user: models.User | None = Depends(get_current_user_optional),
) -> None:
    """Allow access if X-Admin-Token matches ADMIN_TOKEN or if JWT user email is in ADMIN_EMAILS."""
    if _verify_admin_token(x_admin_token):
        return
    if current_user and (current_user.email or "").strip().lower() in _admin_emails():
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin token",
    )


@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    """List all users (admin only)."""
    users = db.query(models.User).order_by(models.User.id).all()
    return [schemas.AdminUserOut.model_validate(u) for u in users]


@router.post("/upgrade-user")
def upgrade_user(
    payload: schemas.AdminUpgradeUserRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
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


@router.get("/trial-ip-whitelist", response_model=list[schemas.AdminTrialIpWhitelistOut])
def list_trial_ip_whitelist(
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    rows = db.query(models.TrialIpWhitelist).order_by(models.TrialIpWhitelist.id).all()
    return [schemas.AdminTrialIpWhitelistOut.model_validate(r) for r in rows]


@router.post("/trial-ip-whitelist", response_model=schemas.AdminTrialIpWhitelistOut)
def add_trial_ip_whitelist(
    payload: schemas.AdminTrialIpWhitelistIn,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    ip = (payload.ip_address or "").strip()
    if not ip:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ip_address is required")
    existing = db.query(models.TrialIpWhitelist).filter(models.TrialIpWhitelist.ip_address == ip).first()
    if existing:
        existing.label = payload.label
        db.commit()
        db.refresh(existing)
        return schemas.AdminTrialIpWhitelistOut.model_validate(existing)

    row = models.TrialIpWhitelist(ip_address=ip, label=payload.label)
    db.add(row)
    db.commit()
    db.refresh(row)
    return schemas.AdminTrialIpWhitelistOut.model_validate(row)


@router.delete("/trial-ip-whitelist/{row_id}")
def delete_trial_ip_whitelist(
    row_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    row = db.get(models.TrialIpWhitelist, row_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Whitelist entry not found")
    db.delete(row)
    db.commit()
    return {"detail": "Whitelist entry deleted."}


@router.post("/users/{user_id}/block")
def block_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
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
    _: None = Depends(_require_admin),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_blocked = False
    db.commit()
    return {"detail": "User unblocked.", "email": user.email}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    delete_user_and_data(user_id, db)
    db.commit()
    return {"detail": "User deleted.", "email": user.email}

