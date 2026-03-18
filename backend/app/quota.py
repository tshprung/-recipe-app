"""Enforce user or trial quota for expensive endpoints (create/adapt/what-can-I-make)."""
from datetime import datetime, timezone

from fastapi import Request, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .auth import decode_trial_token

# Keep in sync with frontend AuthContext MAX_TRIAL_ACTIONS
MAX_TRIAL_ACTIONS = 5
TRIAL_EXHAUSTED_DETAIL = "Free trial finished; please register"
TRIAL_EXHAUSTED_CODE = "trial_exhausted"

_UNLIMITED_QUOTA_EMAIL = "tshprung@gmail.com"


def _has_unlimited_quota(user: models.User) -> bool:
    return (user.email or "").strip().lower() == _UNLIMITED_QUOTA_EMAIL


def _get_trial_token_from_request(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    if not auth.strip().lower().startswith("bearer "):
        return None
    return auth[7:].strip()


def enforce_trial_or_user_quota(
    request: Request,
    db: Session,
    current_user: models.User | None,
    allow_overdraft: bool = False,
) -> models.TrialSession | None:
    """
    Enforce quota: if user is present, check user quota (do not increment here).
    If no user, require valid trial token, load TrialSession, check used_actions < MAX,
    increment used_actions and last_seen_at, commit, and return the TrialSession.
    Raises 401 for invalid/missing trial token, 402 for quota exceeded (user or trial).
    Returns the TrialSession when in trial mode, else None.
    """
    if current_user is not None:
        # User path: only check (increment is done in endpoint after success)
        user_for_update = (
            db.execute(select(models.User).where(models.User.id == current_user.id))
            .scalar_one()
        )
        if (not allow_overdraft) and not _has_unlimited_quota(current_user) and user_for_update.transformations_limit != -1 and (
            user_for_update.transformations_used >= user_for_update.transformations_limit
        ):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="You have reached the free recipes limit. Contact the administrator.",
            )
        return None

    # Trial path: require Bearer trial token
    token = _get_trial_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid trial token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_trial_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid trial token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_id = payload.get("sub")
    if not token_id or not isinstance(token_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid trial token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    trial_session = (
        db.execute(
            select(models.TrialSession).where(models.TrialSession.token_id == token_id)
        )
        .scalars()
        .first()
    )
    if not trial_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid trial token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if trial_session.used_actions >= MAX_TRIAL_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"message": TRIAL_EXHAUSTED_DETAIL, "code": TRIAL_EXHAUSTED_CODE},
            headers={"X-Trial-Exhausted": "1"},
        )
    trial_session.used_actions += 1
    trial_session.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trial_session)
    return trial_session
