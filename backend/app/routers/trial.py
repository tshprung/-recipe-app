"""Anonymous trial: start session, get 3 starter recipes and 5 free actions."""
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Body, Request, HTTPException, status, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import create_trial_token
from ..database import get_db
from ..services.starter_recipes import get_starter_recipes, add_starter_recipes_to_trial_session

router = APIRouter(prefix="/api/trial", tags=["trial"])

MAX_TRIAL_ACTIONS = 5
MAX_TRIAL_SESSIONS_PER_IP_24H = 3
IP_GEO_URL = "http://ip-api.com/json"


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _geo_from_ip(client_ip: str | None) -> dict:
    """Return country_code (and optionally city/zip) from IP; same service as /api/meta/geo."""
    if not client_ip or client_ip in ("127.0.0.1", "::1"):
        return {"country_code": None}
    try:
        resp = httpx.get(
            f"{IP_GEO_URL}/{client_ip}",
            params={"fields": "status,countryCode", "lang": "en"},
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {"country_code": None}
    if data.get("status") != "success":
        return {"country_code": None}
    code = (data.get("countryCode") or "").strip().upper()
    return {"country_code": code or None}


def _language_from_country(country_code: str) -> str:
    if not country_code:
        return "en"
    c = country_code.upper()
    if c == "PL":
        return "pl"
    if c == "IL":
        return "he"
    return "en"


@router.post("/start", response_model=schemas.TrialStartOut)
def trial_start(
    request: Request,
    body: schemas.TrialStartRequest | None = Body(None),
    db: Session = Depends(get_db),
):
    """
    Start or resume an anonymous trial. If device_id is sent and matches an existing
    session, return that session's token and remaining credits (no new trial). Otherwise
    create a new session and return device_id for the client to store.
    """
    body = body or schemas.TrialStartRequest()
    device_id = (body.device_id or "").strip() or None

    # Resume existing trial by device_id (same device, same credits after sign-out)
    if device_id:
        session = db.query(models.TrialSession).filter(
            models.TrialSession.device_id == device_id,
        ).first()
        if session:
            trial_token = create_trial_token(session.token_id)
            remaining = max(0, MAX_TRIAL_ACTIONS - session.used_actions)
            recipes = (
                db.query(models.Recipe)
                .filter(models.Recipe.trial_session_id == session.id)
                .order_by(models.Recipe.id)
                .all()
            )
            recipes_out = [
                schemas.TrialRecipeOut(
                    id=r.id,
                    title=r.title_pl or "Recipe",
                    ingredients=r.ingredients_pl or [],
                    steps=r.steps_pl or [],
                    author_name=r.author_name,
                    author_bio=r.author_bio,
                    author_image_url=r.author_image_url,
                    image_url=r.image_url,
                    diet_tags=r.diet_tags or [],
                )
                for r in recipes
            ]
            return schemas.TrialStartOut(
                trial_token=trial_token,
                country=session.country,
                language=session.language,
                recipes=recipes_out,
                remaining_actions=remaining,
                device_id=device_id,
            )

    client_ip = _client_ip(request)
    geo = _geo_from_ip(client_ip)
    country_code = geo.get("country_code") or "PL"
    language = _language_from_country(country_code)

    # IP guard: last 24h
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    if client_ip:
        whitelisted = db.scalar(
            select(models.TrialIpWhitelist.id).where(
                models.TrialIpWhitelist.ip_address == client_ip
            )
        )
        if not whitelisted:
            count = db.scalar(
                select(func.count(models.TrialSession.id)).where(
                    models.TrialSession.ip_address == client_ip,
                    models.TrialSession.created_at >= cutoff,
                )
            ) or 0
            if count >= MAX_TRIAL_SESSIONS_PER_IP_24H:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many trial sessions from this device.",
                )

    token_id = secrets.token_urlsafe(16)[:32]
    new_device_id = secrets.token_urlsafe(24)[:48]
    now = datetime.now(timezone.utc)
    session = models.TrialSession(
        token_id=token_id,
        device_id=new_device_id,
        country=country_code,
        language=language,
        used_actions=0,
        ip_address=client_ip,
        created_at=now,
        last_seen_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    trial_token = create_trial_token(token_id)
    recipes_data = get_starter_recipes(country_code, language)
    created_recipes = add_starter_recipes_to_trial_session(session, recipes_data[:3], db)
    db.refresh(session)
    recipes_out = [
        schemas.TrialRecipeOut(
            id=recipe.id,
            title=recipe.title_pl or "Recipe",
            ingredients=recipe.ingredients_pl or [],
            steps=recipe.steps_pl or [],
            author_name=recipe.author_name,
            author_bio=recipe.author_bio,
            author_image_url=recipe.author_image_url,
            image_url=recipe.image_url,
            diet_tags=recipe.diet_tags or [],
        )
        for recipe in created_recipes
    ]
    return schemas.TrialStartOut(
        trial_token=trial_token,
        country=country_code,
        language=language,
        recipes=recipes_out,
        remaining_actions=MAX_TRIAL_ACTIONS,
        device_id=new_device_id,
    )
