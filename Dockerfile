FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install backend dependencies first (build cache friendly)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the whole project (backend + frontend, though we only run backend here)
COPY . .

# Railway injects PORT (e.g. 8080). App listens on $PORT; proxy must use same port.
EXPOSE 8080

CMD ["sh", "backend/scripts/railway_start.sh"]

