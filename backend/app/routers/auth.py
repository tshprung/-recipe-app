from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import hash_password, verify_password, create_access_token, get_current_user
from ..database import get_db
from ..services.email import send_verification_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = models.User(
        email=payload.email,
        password_hash=hash_password(payload.password),
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
    except Exception:
        # User is created even if email sending fails; frontend can trigger resend.
        pass

    return user


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()

    # If user exists, check for lockout first
    if user and user.lockout_until and user.lockout_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto zablokowane. Spróbuj ponownie za 15 minut.",
        )

    if not user or not verify_password(payload.password, user.password_hash):
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
            detail="Nieprawidłowy lub wygasły token weryfikacyjny.",
        )

    expires = user.verification_token_expires
    # Normalise timezone to avoid naive/aware comparison issues
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowy lub wygasły token weryfikacyjny.",
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()

    return {"detail": "Adres email został zweryfikowany."}


@router.post("/resend-verification")
def resend_verification(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adres email jest już zweryfikowany.",
        )

    token = str(uuid.uuid4())
    current_user.verification_token = token
    current_user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()

    try:
        send_verification_email(current_user.email, token)
    except Exception:
        pass

    return {"detail": "Wiadomość weryfikacyjna została ponownie wysłana."}
