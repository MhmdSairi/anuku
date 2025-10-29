
# Dockerfile at repo root (multi-stage)
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Install system deps (if any needed by pycryptodome)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libffi-dev && rm -rf /var/lib/apt/lists/*

# Copy original CLI (kept intact)
COPY . /app

# Install original requirements + web requirements
RUN pip install --no-cache-dir -r requirements.txt || true
RUN pip install --no-cache-dir -r requirements-web.txt

# Runtime
EXPOSE 8000
ENV PORT=8000
CMD ["uvicorn", "webapp.app:app", "--host", "0.0.0.0", "--port", "8000"]
