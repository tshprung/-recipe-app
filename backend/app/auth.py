import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import select

from .database import get_db
from . import models

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
# Default 7 days so "Keep me logged in" / OAuth sessions persist across browser closes
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _prehash(password: str) -> str:
    # bcrypt silently truncates at 72 bytes in v5+; SHA-256 pre-hashing avoids the limit
    return base64.b64encode(hashlib.sha256(password.encode()).digest()).decode()


def hash_password(password: str) -> str:
    return pwd_context.hash(_prehash(password))


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(_prehash(plain), hashed)


def hash_password_from_prehashed(password_hash: str) -> str:
    """Store a client-side prehashed value (SHA-256 + base64). No double prehash."""
    return pwd_context.hash(password_hash)


def verify_password_from_prehashed(password_hash: str, hashed: str) -> bool:
    """Verify using client-side prehashed value. No double prehash."""
    return pwd_context.verify(password_hash, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


# Trial tokens: 7-day expiry, type "trial", sub = token_id (<=32 chars)
TRIAL_TOKEN_EXPIRE_DAYS = 7


def create_trial_token(token_id: str) -> str:
    if len(token_id) > 32:
        raise ValueError("token_id must be <= 32 characters")
    expire = datetime.now(timezone.utc) + timedelta(days=TRIAL_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": token_id, "type": "trial", "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_trial_token(token: str) -> dict | None:
    """Verify signature and algorithm, ensure type == 'trial'. Return payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "trial":
            return None
        return payload
    except JWTError:
        return None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.get(models.User, int(user_id))
    if user is None:
        raise credentials_exception
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled. Contact support.",
        )
    return user


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> models.User | None:
    """Return the current user if a valid user JWT is present, else None. Trial tokens are treated as no user (quota handled separately)."""
    if not token or not token.strip():
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") == "trial":
            return None  # Trial token: no user, quota enforced via enforce_trial_or_user_quota
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    user = db.get(models.User, uid)
    if user is None or user.is_blocked:
        return None
    return user


def get_optional_user_and_trial(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> tuple[models.User | None, models.TrialSession | None]:
    """Return (user, None) if valid user JWT, (None, trial_session) if valid trial token, else (None, None)."""
    if not token or not token.strip():
        return (None, None)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return (None, None)
    if payload.get("type") == "trial":
        token_id = payload.get("sub")
        if not token_id or not isinstance(token_id, str):
            return (None, None)
        trial_session = (
            db.execute(select(models.TrialSession).where(models.TrialSession.token_id == token_id))
            .scalars()
            .first()
        )
        return (None, trial_session)
    user_id = payload.get("sub")
    if user_id is None:
        return (None, None)
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return (None, None)
    user = db.get(models.User, uid)
    if user is None or user.is_blocked:
        return (None, None)
    return (user, None)
