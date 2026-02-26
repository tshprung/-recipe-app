from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine, Base
from .routers import auth, users, recipes, shopping_lists, substitutions

# Create tables on startup (dev convenience; use Alembic for production)
Base.metadata.create_all(bind=engine)


def _run_migrations(engine):
    with engine.connect() as conn:
        for col_sql in [
            "ALTER TABLE ingredient_substitutions ADD COLUMN created_by_user_id INTEGER REFERENCES users(id)",
            "ALTER TABLE ingredient_substitutions ADD COLUMN created_at DATETIME",
        ]:
            try:
                conn.execute(text(col_sql))
                conn.commit()
            except Exception:
                pass  # column already exists


_run_migrations(engine)

app = FastAPI(title="Recipe Translator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(recipes.router)
app.include_router(shopping_lists.router)
app.include_router(substitutions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
