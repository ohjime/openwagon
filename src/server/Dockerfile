# ---------- Stage 1: build Vite/Tailwind assets ----------
FROM node:20-slim AS assets
WORKDIR /app/vite
COPY vite/package.json vite/package-lock.json ./
RUN npm ci
COPY vite/ ./
# Tailwind (vite/assets/css/main.css) scans the Django templates via
# `@source "../../../src"`, so the app source must exist at /app/src during the
# build — otherwise Tailwind finds no classes and emits a near-empty stylesheet
# (JS works but the site renders completely unstyled).
COPY src /app/src
RUN npm run build                      # -> /app/vite/static (incl. manifest.json)

# ---------- Stage 2: Python runtime with GeoDjango native libraries ----------
FROM python:3.13-slim-bookworm AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_COMPILE_BYTECODE_TIMEOUT=0 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system \
    DEBUG=False \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app

# GeoDjango needs GDAL/GEOS/PROJ at runtime; Django auto-detects them on Linux.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gdal-bin libgdal-dev libgeos-dev libproj-dev proj-bin binutils \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so this layer caches across source-only changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# App source + the assets built in stage 1
COPY src ./src
COPY --from=assets /app/vite/static ./vite/static
RUN uv sync --frozen --no-dev

# Bake static files into the image (WhiteNoise serves them; needs no DB or AWS creds)
RUN python src/main.py collectstatic --noinput

EXPOSE 8000
# Default command = web (2 workers). docker-compose overrides `command` for the
# release (migrate + cache table + admin) and worker (django-tasks) services, and
# re-specifies web with $WEB_CONCURRENCY workers. Migrations run in `release`, not
# here, so the image alone never touches the database on start.
CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn_worker.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "2", "--chdir", "src", \
     "--access-logfile", "-", "--log-level", "warning"]
