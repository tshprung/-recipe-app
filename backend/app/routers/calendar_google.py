"""Google Calendar integration: OAuth connect/callback, status, and exporting meal plans."""
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/calendar/google", tags=["calendar"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Minimal scope for creating events
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events"


def _frontend_url(path: str = "", query: dict | None = None) -> str:
    base = (os.getenv("FRONTEND_URL") or "").rstrip("/")
    if not base:
        return ""
    url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
    if query:
        url += "?" + urlencode(query)
    return url


def _redirect_uri() -> str:
    base = (os.getenv("GOOGLE_CALENDAR_REDIRECT_BASE") or os.getenv("OAUTH_REDIRECT_BASE") or "").rstrip("/")
    if not base:
        return ""
    return f"{base}/api/calendar/google/callback"


def _state_token(user_id: int) -> str:
    secret = os.getenv("SECRET_KEY", "change-me-in-production")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "typ": "google_calendar_state",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _decode_state(token: str) -> int:
    secret = os.getenv("SECRET_KEY", "change-me-in-production")
    try:
        data = jwt.decode(token, secret, algorithms=["HS256"])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state") from e
    if data.get("typ") != "google_calendar_state":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    sub = data.get("sub")
    try:
        return int(sub)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state") from e


def _refresh_access_token(refresh_token: str) -> str:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Google Calendar is not configured")
    try:
        resp = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            raise ValueError("No access_token")
        return access_token
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail="Failed to refresh Google access token") from e


def _create_event(access_token: str, calendar_id: str, event: dict) -> None:
    url = GOOGLE_CALENDAR_EVENTS_URL.format(calendarId=calendar_id)
    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=event,
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail="Failed to create Google Calendar event") from e


@router.get("/status")
def status_google_calendar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    row = (
        db.query(models.GoogleOAuthToken)
        .filter(models.GoogleOAuthToken.user_id == current_user.id)
        .order_by(models.GoogleOAuthToken.updated_at.desc())
        .first()
    )
    return {"connected": bool(row)}


@router.get("/connect")
def connect_google_calendar(
    request: Request,
    current_user: models.User = Depends(get_current_user),
):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = _redirect_uri()
    front = _frontend_url("/meal-plan")
    if not client_id or not redirect_uri:
        # redirect back to app with error
        return RedirectResponse(url=_frontend_url("/meal-plan", {"error": "google_calendar_not_configured"}) or (front or "/"))
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": CALENDAR_SCOPE,
        "access_type": "offline",
        "prompt": "consent",  # ensure refresh_token is returned
        "state": _state_token(current_user.id),
    }
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/callback")
def callback_google_calendar(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error or not code or not state:
        return RedirectResponse(url=_frontend_url("/meal-plan", {"error": "google_calendar_denied"}) or "/")

    user_id = _decode_state(state)

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = _redirect_uri()
    if not all([client_id, client_secret, redirect_uri]):
        return RedirectResponse(url=_frontend_url("/meal-plan", {"error": "google_calendar_not_configured"}) or "/")

    try:
        resp = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        refresh_token = data.get("refresh_token")
        scope = data.get("scope")
        if not refresh_token:
            # If user already consented earlier, Google may omit refresh_token unless prompt=consent.
            raise ValueError("No refresh_token returned by Google")
    except Exception:
        return RedirectResponse(url=_frontend_url("/meal-plan", {"error": "google_calendar_failed"}) or "/")

    now = datetime.now(timezone.utc)
    existing = (
        db.query(models.GoogleOAuthToken)
        .filter(models.GoogleOAuthToken.user_id == user_id)
        .first()
    )
    if existing:
        existing.refresh_token = refresh_token
        existing.scope = scope
        existing.updated_at = now
    else:
        db.add(
            models.GoogleOAuthToken(
                user_id=user_id,
                provider="google",
                refresh_token=refresh_token,
                scope=scope,
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()

    return RedirectResponse(url=_frontend_url("/meal-plan", {"google_calendar": "connected"}) or "/")


@router.post("/export/meal-plan/{plan_id}")
def export_meal_plan_to_calendar(
    plan_id: int,
    calendar_id: str | None = None,  # optional; default primary
    default_time: str | None = None,  # "19:00"
    timezone_name: str | None = None,  # e.g. "Europe/Warsaw"
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create Google Calendar events for each meal in a meal plan (MVP: create-only, no updates)."""
    token_row = (
        db.query(models.GoogleOAuthToken)
        .filter(models.GoogleOAuthToken.user_id == current_user.id)
        .order_by(models.GoogleOAuthToken.updated_at.desc())
        .first()
    )
    if not token_row:
        raise HTTPException(status_code=400, detail="Google Calendar is not connected")

    plan = db.get(models.MealPlan, plan_id)
    if not plan or plan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Meal plan not found")

    cal_id = (calendar_id or "").strip() or "primary"
    tz = (timezone_name or "").strip() or "UTC"
    tm = (default_time or "").strip() or "19:00"
    # MVP: create 1-hour events; user can adjust in calendar
    start_suffix = f"T{tm}:00"
    end_suffix = f"T{tm}:00"

    access_token = _refresh_access_token(token_row.refresh_token)

    days = plan.data.get("days") or []
    created = 0
    for d in days:
        date_str = (d.get("date") or "").strip()
        meals = d.get("meals") or []
        if not date_str or not isinstance(meals, list):
            continue
        for meal in meals:
            if not isinstance(meal, dict):
                continue
            title = (meal.get("title") or meal.get("name") or "").strip() or "Meal"
            meal_type = (meal.get("meal_type") or "").strip()
            summary = f"{meal_type.title().replace('_', ' ')}: {title}" if meal_type else title
            description_parts = []
            if meal.get("short_description"):
                description_parts.append(str(meal.get("short_description")).strip())
            ings = meal.get("ingredients") or []
            if isinstance(ings, list) and ings:
                description_parts.append("Ingredients:\\n- " + "\\n- ".join(str(x) for x in ings if x))
            steps = meal.get("steps") or []
            if isinstance(steps, list) and steps:
                description_parts.append("Steps:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps) if s))
            description = "\\n\\n".join([p for p in description_parts if p])

            event = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": f"{date_str}{start_suffix}", "timeZone": tz},
                "end": {"dateTime": f"{date_str}{end_suffix}", "timeZone": tz},
            }
            _create_event(access_token, cal_id, event)
            created += 1

    return {"created_events": created}

