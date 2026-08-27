FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Non-root runtime user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# 1 worker: the in-memory SSE broker is per-process. Scale horizontally only
# after moving the event broker to Redis (see README).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
