# syntax=docker/dockerfile:1
# AdaRag API image — CUDA torch for in-container GPU (run the api service with --gpus all).
FROM python:3.12-slim

# libgomp1: OpenMP runtime torch/numpy/scipy load at import. libglib2.0-0: OpenCV (easyocr) runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# uv for fast, locked installs (copied from the official uv image).
COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

ENV UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies first so this layer caches until the lockfile changes. The BuildKit cache
# mount keeps uv's wheel cache across builds, so a lockfile change only fetches what actually changed.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Application source.
COPY . .

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
