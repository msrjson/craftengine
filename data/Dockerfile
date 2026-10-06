FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so the layer caches across code changes.
# The framework package is `engine/` (imported as `craft.*`) — it was renamed
# from `services/`, and before that a `COPY src/ ./src/` pointed at a directory
# that never existed and failed the build outright.
COPY pyproject.toml .
COPY README.md .
COPY engine/ ./engine/
# `[dev]` brings pytest and httpx — this is the development image, and the
# suite is meant to be runnable inside it. Dockerfile.prod installs runtime
# dependencies only.
RUN pip install --no-cache-dir ".[dev]"

# Copy codebase
COPY . .

EXPOSE 9000

# Forward-only database migrations and start server on default port 9000
CMD ["sh", "-c", "python dev.py migrate && python dev.py serve --host 0.0.0.0 --port 9000 --no-reload"]
