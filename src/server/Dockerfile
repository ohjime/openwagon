# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the Vite front-end assets
# ---------------------------------------------------------------------------
FROM node:20-slim AS vite
WORKDIR /build
COPY src/server/vite/package*.json ./
RUN npm install
COPY src/server/vite/ ./
# vite.config.js outDir = ./static  ->  /build/static (with manifest.json)
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
COPY --from=vite /build/static /app/src/server/vite/static

# Collect static files into staticfiles/ (WhiteNoise compressed-manifest storage,
# selected because DEBUG=false). No database access here.
RUN uv run --no-sync src/main.py collectstatic --noinput

EXPOSE 8000
CMD ["/app/bin/runserver_prod.sh"]
