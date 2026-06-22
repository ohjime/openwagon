# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the Vite front-end assets
# ---------------------------------------------------------------------------
FROM node:20-slim AS vite
WORKDIR /app/vite
COPY src/server/vite/package*.json ./
RUN npm install
COPY src/server/vite/ ./
# Tailwind (vite/assets/css/main.css) scans the Django templates via
# `@source "../../../src"`, so the app source must exist at /app/src during the
# build — otherwise Tailwind finds no classes and emits a near-empty stylesheet
# (JS works but the site renders completely unstyled).
COPY src/server/src /app/src
# vite.config.js outDir = ./static  ->  /app/vite/static (with manifest.json)
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — Python runtime with GeoDjango native libraries
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS runtime

# GeoDjango needs GDAL/GEOS/PROJ at runtime; Django auto-detects them on Linux.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gdal-bin libgdal-dev libgeos-dev libproj-dev proj-bin binutils \
    && rm -rf /var/lib/apt/lists/*

# uv (standalone binaries from the official image).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system \
    DEBUG=false

WORKDIR /app/src/server

# Install Python deps first (cached unless pyproject/uv.lock change).
COPY src/server/pyproject.toml src/server/uv.lock ./
RUN uv sync --no-dev --frozen

# Application source + helper scripts.
COPY src/server/ /app/src/server/
COPY bin/ /app/bin/

# Built Vite assets from stage 1 (the .dockerignore keeps the source tree's
# vite/static out, so this is the only copy).
COPY --from=vite /app/vite/static /app/src/server/vite/static

# Collect static files into staticfiles/ (WhiteNoise compressed-manifest storage,
# selected because DEBUG=false). No database access here.
RUN uv run --no-sync src/main.py collectstatic --noinput

EXPOSE 8000
# Default command = web (2 workers). docker-compose overrides `command` for the
# release (migrate + cache table + admin) and worker (django-tasks) services, and
# re-specifies web with $WEB_CONCURRENCY workers. Migrations run in `release`, not
# here, so the image alone never touches the database on start.
CMD ["uv", "run", "--no-sync", "gunicorn", "config.asgi:application", \
     "-k", "uvicorn_worker.UvicornWorker", "--bind", "0.0.0.0:8000", \
     "--workers", "2", "--chdir", "src", \
     "--access-logfile", "-", "--log-level", "warning"]
