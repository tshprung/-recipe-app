import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from .database import engine, Base
from .routers import auth, users, recipes, shopping_lists, substitutions, admin

# Create tables on startup (dev convenience; use Alembic for production)
Base.metadata.create_all(bind=engine)


def _run_migrations(engine):
    """Best-effort lightweight migrations for dev SQLite DB."""
    with engine.connect() as conn:
        statements = [
            # Ingredient substitutions (older migration)
            "ALTER TABLE ingredient_substitutions ADD COLUMN created_by_user_id INTEGER REFERENCES users(id)",
            "ALTER TABLE ingredient_substitutions ADD COLUMN created_at DATETIME",
            # User quota / verification / security columns
            "ALTER TABLE users ADD COLUMN transformations_used INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN transformations_limit INTEGER NOT NULL DEFAULT 5",
            "ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN verification_token VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN verification_token_expires DATETIME",
            "ALTER TABLE users ADD COLUMN account_tier VARCHAR(50) NOT NULL DEFAULT 'free'",
            "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN lockout_until DATETIME",
        ]
        for sql in statements:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                # Column likely already exists; ignore for idempotency
                pass


_run_migrations(engine)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[] if os.getenv("TESTING") else ["10/minute"],
)

app = FastAPI(title="Recipe Translator API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(
        status_code=429,
        content={"detail": "Zbyt wiele żądań. Spróbuj ponownie później."},
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(recipes.router)
app.include_router(shopping_lists.router)
app.include_router(substitutions.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}
