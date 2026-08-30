# syntax=docker/dockerfile:1

# ------------------------------------------------------------------------------
# Backend image: FastAPI + Uvicorn
# Multi-stage: build wheels in a full image, run on a slim, non-root image.
# ------------------------------------------------------------------------------

# --- Builder ------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install dependencies into an isolated prefix so we can copy just what's needed.
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


# --- Runtime ------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Do not buffer stdout/stderr so logs stream to the container runtime immediately.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    DATABASE_URL=sqlite:////data/diet_planner.db

# Create a non-root user and a writable data dir for the SQLite file.
RUN groupadd --system app \
    && useradd --system --gid app --home /app app \
    && mkdir -p /data \
    && chown -R app:app /data

WORKDIR /app

# Copy installed dependencies from the builder.
COPY --from=builder /install /usr/local

# Copy application source.
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

# Container-level healthcheck hits the app's readiness probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
    sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status==200 else sys.exit(1)"

# Uvicorn is sufficient for this workload; scale horizontally via replicas.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
