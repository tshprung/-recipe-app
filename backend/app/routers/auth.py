import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import (
    hash_password_from_prehashed,
    verify_password_from_prehashed,
    create_access_token,
    get_current_user,
)
from ..database import get_db
from ..services.email import send_verification_email
from ..services.starter_recipes import ensure_starter_recipes_for_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
# Cloudflare test secret: always passes validation (use real key in production)
TURNSTILE_TEST_SECRET = "1x0000000000000000000000000000000AA"


def _verify_turnstile(token: str, remote_ip: str | None) -> bool:
    secret = os.getenv("TURNSTILE_SECRET_KEY") or TURNSTILE_TEST_SECRET
    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    try:
        resp = httpx.post(TURNSTILE_VERIFY_URL, json=payload, timeout=10.0)
        data = resp.json()
        return data.get("success") is True
    except Exception as e:
        logger.warning("Turnstile verification failed: %s", e)
        return False


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(
    request: Request,
    payload: schemas.UserRegister,
    db: Session = Depends(get_db),
):
    # Always require captcha (widget uses test key when VITE_TURNSTILE_SITE_KEY not set)
    if not payload.captcha_token or not payload.captcha_token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete the verification challenge.",
        )
    client_host = request.client.host if request.client else None
    if not _verify_turnstile(payload.captcha_token, client_host):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification failed. Refresh and try again.",
        )

    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = models.User(
        email=payload.email,
        password_hash=hash_password_from_prehashed(payload.password_hash),
        ui_language=(payload.ui_language or "en"),
        target_language=payload.target_language,
        target_country=payload.target_country,
        target_city=payload.target_city,
        target_zip=payload.target_zip,
        dish_preferences=payload.dish_preferences or [],
        default_servings=payload.default_servings if payload.default_servings is not None else 4,
        allergens=payload.allergens or [],
        custom_allergens_text=payload.custom_allergens_text,
        household_adults=payload.household_adults,
        household_kids=payload.household_kids,
        diet_filters=payload.diet_filters or [],
    )

    # Generate verification token (24h expiry)
    token = str(uuid.uuid4())
    user.verification_token = token
    user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        send_verification_email(user.email, token)
    except Exception as e:
        logger.exception("Failed to send verification email to %s", user.email)
        msg = str(e) if e else ""
        # Keep error actionable without dumping internals.
        if "RESEND_" in msg or "Resend" in msg:
            detail = f"Failed to send verification email. {msg}"
        else:
            detail = (
                "Failed to send verification email. Use “Resend verification email” in Settings."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        ) from e

    return user


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()

    # If user exists, check for lockout first (normalise tz for SQLite naive datetimes)
    now = datetime.now(timezone.utc)
    if user and user.lockout_until:
        lockout = user.lockout_until
        if lockout.tzinfo is None:
            lockout = lockout.replace(tzinfo=timezone.utc)
        if lockout > now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account locked. Try again in 15 minutes.",
            )

    if not user or not verify_password_from_prehashed(payload.password_hash, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.lockout_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Successful login resets counters
    user.failed_login_attempts = 0
    user.lockout_until = None
    db.commit()

    # Starter recipes are no longer created automatically on login.
    # Users can still add them explicitly from Settings (/users/me/fetch-starter-recipes)
    # or via onboarding claim flows.
    return {"access_token": create_access_token(user.id)}


@router.post("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    user = (
        db.query(models.User)
        .filter(
            models.User.verification_token == token,
            models.User.verification_token_expires != None,  # noqa: E711
        )
        .first()
    )
    if not user or not user.verification_token_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        )

    expires = user.verification_token_expires
    # Normalise timezone to avoid naive/aware comparison issues
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()

    return {"detail": "Email address has been verified."}


@router.post("/resend-verification")
def resend_verification(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already verified.",
        )

    token = str(uuid.uuid4())
    current_user.verification_token = token
    current_user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()

    try:
        send_verification_email(current_user.email, token)
    except Exception as e:
        logger.exception("Failed to resend verification email to %s", current_user.email)
        msg = str(e) if e else ""
        if "RESEND_" in msg or "Resend" in msg:
            detail = f"Failed to send verification email. {msg}"
        else:
            detail = "Failed to send verification email. Check Resend configuration on the server."
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        ) from e

    return {"detail": "Verification email has been resent."}


# --- OAuth (Google, Facebook) ---

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

FACEBOOK_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
FACEBOOK_USERINFO_URL = "https://graph.facebook.com/me?fields=id,email,name"


def _oauth_redirect_uri(provider: str) -> str:
    base = (os.getenv("OAUTH_REDIRECT_BASE") or "").rstrip("/")
    if not base:
        return ""
    return f"{base}/api/auth/{provider}/callback"


def _frontend_url(path: str = "", query: dict | None = None) -> str:
    base = (os.getenv("FRONTEND_URL") or "").rstrip("/")
    if not base:
        return ""
    url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
    if query:
        url += "?" + urlencode(query)
    return url


def _get_or_create_oauth_user(db: Session, email: str, name: str | None) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        return user
    # New user via OAuth: no email verification needed (provider already verified). Placeholder password so they cannot log in with email/password until they set one.
    placeholder = secrets.token_urlsafe(32)
    user = models.User(
        email=email,
        password_hash=hash_password_from_prehashed(placeholder),
        is_verified=True,  # OAuth provider verified the email
        ui_language="en",
        target_language="pl",
        target_country="PL",
        target_city="Wrocław",
        target_zip=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ----- Google -----

@router.get("/google")
def google_login(request: Request):
    """Redirect to Google OAuth consent screen."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = _oauth_redirect_uri("google")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login is not configured")
    state = secrets.token_urlsafe(16)
    # Store state in something durable if you need to verify it in callback (e.g. redis).
    # For minimal setup we skip state verification; in production you should verify state.
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        # No "prompt": returning users who already approved may skip the consent screen and stay logged in
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/google/callback")
def google_callback(code: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    if error or not code:
        front = _frontend_url("/signin", {"error": "google_denied"})
        return RedirectResponse(url=front if front else "/signin")
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = _oauth_redirect_uri("google")
    if not all([client_id, client_secret, redirect_uri]):
        front = _frontend_url("/signin", {"error": "config"})
        return RedirectResponse(url=front if front else "/signin")
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
        access_token = data.get("access_token")
        if not access_token:
            raise ValueError("No access_token in response")
        user_resp = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        user_resp.raise_for_status()
        info = user_resp.json()
        email = (info.get("email") or "").strip()
        if not email:
            raise ValueError("Google did not return email")
        name = (info.get("name") or "").strip() or None
    except Exception as e:
        logger.warning("Google OAuth error: %s", e)
        front = _frontend_url("/signin", {"error": "google_failed"})
        return RedirectResponse(url=front if front else "/signin")
    user = _get_or_create_oauth_user(db, email, name)
    # Do not run ensure_starter_recipes here — it can take several seconds (AI call) and delays redirect.
    # Users from onboarding claim pre-fetched recipes on the frontend; others can use "Fetch starter recipes" in Settings.
    token = create_access_token(user.id)
    front = _frontend_url("/signin", {"token": token})
    return RedirectResponse(url=front if front else "/signin")


# ----- Facebook -----

@router.get("/facebook")
def facebook_login(request: Request):
    """Redirect to Facebook OAuth consent screen."""
    app_id = os.getenv("FACEBOOK_APP_ID")
    redirect_uri = _oauth_redirect_uri("facebook")
    if not app_id or not redirect_uri:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Facebook login is not configured")
    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "email,public_profile",
    }
    url = f"{FACEBOOK_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/facebook/callback")
def facebook_callback(code: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    if error or not code:
        front = _frontend_url("/signin", {"error": "facebook_denied"})
        return RedirectResponse(url=front if front else "/signin")
    app_id = os.getenv("FACEBOOK_APP_ID")
    app_secret = os.getenv("FACEBOOK_APP_SECRET")
    redirect_uri = _oauth_redirect_uri("facebook")
    if not all([app_id, app_secret, redirect_uri]):
        front = _frontend_url("/signin", {"error": "config"})
        return RedirectResponse(url=front if front else "/signin")
    try:
        token_resp = httpx.post(
            FACEBOOK_TOKEN_URL,
            data={
                "client_id": app_id,
                "client_secret": app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=10.0,
        )
        token_resp.raise_for_status()
        data = token_resp.json()
        access_token = data.get("access_token")
        if not access_token:
            raise ValueError("No access_token in response")
        user_resp = httpx.get(
            f"{FACEBOOK_USERINFO_URL}&access_token={access_token}",
            timeout=10.0,
        )
        user_resp.raise_for_status()
        info = user_resp.json()
        email = (info.get("email") or "").strip()
        if not email:
            raise ValueError("Facebook did not return email")
        name = (info.get("name") or "").strip() or None
    except Exception as e:
        logger.warning("Facebook OAuth error: %s", e)
        front = _frontend_url("/signin", {"error": "facebook_failed"})
        return RedirectResponse(url=front if front else "/signin")
    user = _get_or_create_oauth_user(db, email, name)
    # Do not run ensure_starter_recipes here — keeps OAuth redirect fast (see Google comment).
    token = create_access_token(user.id)
    front = _frontend_url("/signin", {"token": token})
    return RedirectResponse(url=front if front else "/signin")
