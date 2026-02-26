"""
Test configuration.

Sets DATABASE_URL to a dedicated test SQLite file BEFORE importing any app
modules, so the app engine is created against the test DB.
"""
import os

# --- must happen before any app import ---
os.environ["DATABASE_URL"] = "sqlite:///./test_recipe_app.db"
os.environ["SECRET_KEY"] = "test-secret-for-tests-only"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_recipe_app.db"

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
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        if os.path.exists("./test_recipe_app.db"):
            os.remove("./test_recipe_app.db")
    except PermissionError:
        pass  # Windows holds the file briefly; it will be overwritten next run


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


@pytest.fixture
def registered_user(client):
    r = client.post(
        "/api/auth/register",
        json={"email": SAMPLE_EMAIL, "password": SAMPLE_PASSWORD},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def auth_headers(client, registered_user):
    r = client.post(
        "/api/auth/login",
        json={"email": SAMPLE_EMAIL, "password": SAMPLE_PASSWORD},
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
