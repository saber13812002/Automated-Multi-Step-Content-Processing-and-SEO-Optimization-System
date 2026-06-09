# syntax=docker/dockerfile:1
# Offline-capable multi-stage build.
# Requires wheels/ to be populated before build (see scripts/download-wheels.sh).

# ---------------------------------------------------------------------------
# Stage 1 — install Python deps + app from local wheels (no network)
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY wheels/ /wheels/
COPY requirements.build.txt requirements.docker.txt pyproject.toml README.md ./
COPY ai_benchmarker/ /build/ai_benchmarker/

RUN pip install --no-index --find-links=/wheels \
        --prefix=/install \
        -r requirements.build.txt \
    && pip install --no-index --find-links=/wheels \
        --prefix=/install \
        --no-build-isolation \
        -r requirements.docker.txt \
        /build

# ---------------------------------------------------------------------------
# Stage 2 — minimal runtime image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_LOG_LEVEL=INFO \
    DATABASE_URL=sqlite:////data/ai_benchmarker.db

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /app app \
    && mkdir -p /data \
    && chown -R app:app /app /data

COPY --from=builder /install /usr/local

USER app
WORKDIR /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "ai_benchmarker.app:app", "--host", "0.0.0.0", "--port", "8000"]
