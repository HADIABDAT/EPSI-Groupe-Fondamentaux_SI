FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY novaservices/ novaservices/
COPY templates/ templates/
COPY static/ static/

# Identification de la version, injectée par le pipeline au build.
ARG APP_VERSION=dev
ARG GIT_COMMIT=local
ENV APP_VERSION=${APP_VERSION} \
    GIT_COMMIT=${GIT_COMMIT}

# La base SQLite vit dans /data, monté en volume sur la VM pour survivre aux déploiements.
ENV DATABASE_URL=sqlite:////data/novaservices.db
RUN useradd --create-home appuser && mkdir /data instance && chown appuser /data instance
USER appuser

EXPOSE 8000
# Un seul processus (avec des threads) : SQLite supporte mal plusieurs écrivains.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "app:app"]
