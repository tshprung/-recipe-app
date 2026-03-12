"""
Test configuration.

Sets DATABASE_URL to a dedicated test SQLite file BEFORE importing any app
modules, so the app engine is created against the test DB.
"""
import base64
import hashlib
import os
from pathlib import Path
from unittest.mock import patch

# --- must happen before any app import ---
_TEST_DB_PATH = Path(__file__).resolve().parent / "test_recipe_app.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-for-tests-only"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app import models

TEST_DATABASE_URL = f"sqlite:///{_TEST_DB_PATH.as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    # Ensure we always start from a clean schema (create_all won't alter existing tables).
    try:
        if _TEST_DB_PATH.exists():
            _TEST_DB_PATH.unlink()
    except PermissionError:
        pass
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        if _TEST_DB_PATH.exists():
            _TEST_DB_PATH.unlink()
    except PermissionError:
        pass  # Windows holds the file briefly; it will be overwritten next run


@pytest.fixture(autouse=True)
def _no_recipe_image_generation():
    """Skip recipe image generation in tests (no OpenAI calls, no file I/O)."""
    with patch("app.services.recipe_image.get_or_create_recipe_image"), patch(
        "app.routers.recipes.get_or_create_recipe_image"
    ):
        yield


@pytest.fixture(autouse=True)
def clean_tables():
    """Wipe all rows between tests so each test starts fresh."""
    yield
    db = TestSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


# --- Convenience fixtures ---

SAMPLE_EMAIL = "tester@example.com"
SAMPLE_PASSWORD = "securepassword"


def password_hash(plain: str) -> str:
    """Same as backend _prehash: SHA-256 + base64. Use for login/register payloads."""
    return base64.b64encode(hashlib.sha256(plain.encode()).digest()).decode()


# Dummy captcha token for tests (auth router requires it; we mock verification)
CAPTCHA_DUMMY = "test-captcha-token"


@pytest.fixture
def registered_user(client):
    with patch("app.routers.auth.send_verification_email"), patch(
        "app.routers.auth._verify_turnstile", return_value=True
    ):
        r = client.post(
            "/api/auth/register",
            json={
                "email": SAMPLE_EMAIL,
                "password_hash": password_hash(SAMPLE_PASSWORD),
                "captcha_token": CAPTCHA_DUMMY,
                "ui_language": "en",
                "target_language": "pl",
                "target_country": "PL",
                "target_city": "Wrocław",
                "target_zip": "50-001",
            },
        )
    assert r.status_code == 201
    user_data = r.json()

    # Mark the test user as verified with a generous quota
    db = TestSessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_data["id"]).first()
        user.is_verified = True
        user.transformations_limit = 100
        user.transformations_used = 0
        db.commit()
    finally:
        db.close()

    return user_data


@pytest.fixture
def auth_headers(client, registered_user):
    with patch("app.routers.auth.ensure_starter_recipes_for_user"):
        r = client.post(
            "/api/auth/login",
            json={"email": SAMPLE_EMAIL, "password_hash": password_hash(SAMPLE_PASSWORD)},
        )
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


MOCK_TRANSLATED = {
    "title_pl": "Zupa Pomidorowa",
    "title_original": "מרק עגבניות",
    "ingredients_pl": [
        {"amount": "500g", "name": "pomidory"},
        {"amount": "1 sztuka", "name": "cebula"},
        {"amount": "2 ząbki", "name": "czosnek"},
    ],
    "ingredients_original": [
        {"amount": "500g", "name": "עגבניות"},
    ],
    "steps_pl": [
        "Podsmaż cebulę i czosnek.",
        "Dodaj pomidory i gotuj 20 minut.",
        "Zmiksuj i dopraw do smaku.",
    ],
    "tags": ["zupa", "wegetariańska"],
    "substitutions": {"świeże pomidory": "passata pomidorowa"},
    "notes": {"porcje": "4", "czas_gotowania": "30 min"},
    "detected_language": "he",
}


@pytest.fixture
def recipe(client, auth_headers):
    """Create a recipe via the API (translate_recipe is mocked)."""
    from unittest.mock import patch
    with patch("app.routers.recipes.translate_recipe", return_value=MOCK_TRANSLATED):
        r = client.post(
            "/api/recipes/",
            json={"raw_input": "מרק עגבניות"},
            headers=auth_headers,
        )
    assert r.status_code == 201
    return r.json()
