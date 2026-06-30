# Build context MUST be the REPO ROOT (Railway default when dockerfilePath = backend/Dockerfile).
# docker-compose sets context: . and dockerfile: backend/Dockerfile to match.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

# Writable data dir (sqlite / admin quiniela_<uuid>.csv uploads). CSV is optional at boot.
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# No start.sh in image — avoids missing-file builds; PORT from Railway/compose
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
