import logging
import os
from datetime import datetime, timedelta, timezone
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
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
