"""Onboarding: guest pre-fetch of starter recipes (no auth) and claim after sign-up."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services.starter_recipes import get_starter_recipes

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.post(
    "/prepare-starter-recipes",
    response_model=schemas.OnboardingPrepareResponse,
    status_code=status.HTTP_200_OK,
)
def prepare_starter_recipes(
    request: Request,
    payload: schemas.OnboardingPrepareRequest,
    db: Session = Depends(get_db),
):
    """
    Pre-fetch 3 starter recipes during onboarding (no auth).
    Returns a short-lived claim_token to be sent after registration/login to attach recipes to the user.
    Rate-limited by IP to avoid abuse.
    """
    recipes_data = get_starter_recipes(
        payload.target_country,
        payload.target_language,
        dish_preferences=payload.dish_preferences or None,
    )
    claim_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    row = models.PreparedStarterRecipes(
        claim_token=claim_token,
        recipes_data=recipes_data,
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    return schemas.OnboardingPrepareResponse(claim_token=claim_token)
