import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from .database import engine
from .routers import auth, users, recipes, shopping_lists, substitutions, admin, meta, onboarding

# DB schema is managed via Alembic migrations (production) or test fixtures (tests).

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
        content={"detail": "Too many requests. Try again later."},
    ),
)

# In production set CORS_ORIGINS e.g. https://myrecipes.cloud (comma-separated for multiple)
_cors_origins = os.getenv("CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in _cors_origins.split(",")] if _cors_origins != "*" else ["*"]


def _cors_headers_for_request(request: Request) -> dict:
    """Build CORS headers for preflight/response; reflect origin when allowed."""
    origin = request.headers.get("origin") or ""
    if allow_origins == ["*"]:
        allow_origin = "*"
    elif origin in allow_origins:
        allow_origin = origin
    else:
        allow_origin = allow_origins[0] if allow_origins else "*"
    return {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",
        "Access-Control-Max-Age": "86400",
    }


@app.middleware("http")
async def cors_preflight_first(request: Request, call_next):
    """Handle OPTIONS (CORS preflight) first so it always returns 200; avoids 400 from proxy/downstream."""
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=_cors_headers_for_request(request))
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
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
app.include_router(meta.router)
app.include_router(onboarding.router)


@app.get("/health")
def health():
    return {"status": "ok"}
