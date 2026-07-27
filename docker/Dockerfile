# Minimal image running the FastAPI service for the dataset generator.
FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal; pyarrow/openpyxl ship wheels.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY configs ./configs

ENV PLANNER_BACKEND=heuristic \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
