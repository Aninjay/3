FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    FLASK_ENV=production \
    PORT=5000

RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY ["volunteers CSV.csv", "/app/volunteers CSV.csv"]
COPY --from=frontend-build /app/frontend/dist/ /app/frontend/dist/

RUN useradd --system --create-home --uid 10001 appuser
USER 10001:10001

EXPOSE 5000

CMD ["sh", "-c", "python -m backend.app.db.migrate && python -m backend.app.db.seed && exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --threads 4 --timeout 120 backend.run:app"]
