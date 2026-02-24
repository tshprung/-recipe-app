# Recipe Translator

Transforms Hebrew recipes into Polish with localized ingredient substitutions.

**Stack:** FastAPI + SQLite (backend) · React + Tailwind + Vite (frontend) · JWT auth

---

## Local setup — Windows

### 1. Environment file

```bat
copy .env.example .env
```

Edit `.env` and set a real `SECRET_KEY` (any long random string).

### 2. Backend

**Option A — setup script (one-time):**

```bat
cd backend
setup.bat
```

**Option B — manual:**

```bat
cd backend
C:\Users\Tal\AppData\Local\Programs\Python\Python311\python.exe -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Start the server:**

```bat
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

API: http://localhost:8000
Docs: http://localhost:8000/docs

### 3. Frontend

```bat
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

---

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | JWT signing key — **change this** | `change-me-in-production` |
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:///./recipe_app.db` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL | `60` |
| `OPENAI_API_KEY` | For recipe translation | *(required later)* |
