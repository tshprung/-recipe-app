#!/bin/sh
set -e
PORT="${PORT:-8000}"
echo "PORT=$PORT"
echo "Running migrations..."
alembic -c backend/alembic.ini upgrade head
echo "Starting uvicorn on 0.0.0.0:$PORT"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --app-dir backend
