#!/usr/bin/env bash
# Interactively build env/.env for the docker-compose production stack.
# Mirrors cosound/bin/setup_env.sh, adapted to waygon (PostGIS, Google Maps,
# AWS S3 + SES, Firebase). The generated file is git-ignored — never commit it.
set -euo pipefail

ENV_FILE="env/.env"

# ── helpers ──────────────────────────────────────────────────────────────────

# prompt LABEL VAR [DEFAULT] [secret]  — required (loops until non-empty)
prompt() {
    local label="$1" var="$2" default="${3:-}" secret="${4:-}"
    local value=""
    while [[ -z "$value" ]]; do
        if [[ -n "$default" ]]; then
            printf "%s [%s]: " "$label" "$default"
        else
            printf "%s: " "$label"
        fi
        if [[ "$secret" == "secret" ]]; then
            read -rs value; echo
        else
            read -r value
        fi
        value="${value:-$default}"
        [[ -z "$value" ]] && echo "  (required — please enter a value)"
    done
    printf -v "$var" '%s' "$value"
}

# prompt_optional LABEL VAR [DEFAULT]  — blank allowed (accepts the default or empty)
prompt_optional() {
    local label="$1" var="$2" default="${3:-}" value=""
    printf "%s [%s]: " "$label" "$default"
    read -r value
    printf -v "$var" '%s' "${value:-$default}"
}

# ── guard: overwrite? ─────────────────────────────────────────────────────────

if [[ -f "$ENV_FILE" ]]; then
    printf "\n%s already exists. Overwrite? [y/N]: " "$ENV_FILE"
    read -r confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
fi

mkdir -p env

echo ""
echo "=== waygon production environment setup (env/.env) ==="
echo "Press Enter to accept a [default]. Required fields cannot be left blank."
echo ""

# ── Django ────────────────────────────────────────────────────────────────────
printf "SECRET_KEY — generate automatically? [Y/n]: "
read -r sk_choice
if [[ "$sk_choice" =~ ^[Nn]$ ]]; then
    prompt "SECRET_KEY" SECRET_KEY "" secret
else
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    echo "  Generated."
fi

# SITE_ADDRESS = every hostname Caddy serves (one TLS cert each), comma-separated.
# PROD_HOSTS   = Django ALLOWED_HOSTS/CSRF; a leading dot is a wildcard that covers
#               the apex + all subdomains, so it rarely needs changing.
prompt_optional "SITE_ADDRESS (hostnames for Caddy TLS, comma-separated)" SITE_ADDRESS "waygon.dev, admin.waygon.dev"
prompt_optional "PROD_HOSTS (Django allowed hosts; leading-dot = wildcard)" PROD_HOSTS ".waygon.dev"
# Apex domain (PROD_HOSTS minus any leading dot, first entry) — used for email default.
APEX=$(printf '%s' "$PROD_HOSTS" | sed 's/^\.//' | cut -d, -f1 | tr -d ' ')
prompt_optional "WEB_CONCURRENCY (gunicorn workers)"             WEB_CONCURRENCY "2"
prompt          "GOOGLE_MAPS_API_KEY"                            GOOGLE_MAPS_API_KEY "" secret

# ── Postgres ──────────────────────────────────────────────────────────────────
echo ""
echo "--- Postgres (+ PostGIS) ---"
prompt_optional "POSTGRES_USER" POSTGRES_USER "waygon"
prompt_optional "POSTGRES_DB"   POSTGRES_DB   "waygon_db"
prompt          "POSTGRES_PASSWORD" POSTGRES_PASSWORD "" secret
while true; do
    printf "Confirm POSTGRES_PASSWORD: "
    read -rs pg_confirm; echo
    [[ "$pg_confirm" == "$POSTGRES_PASSWORD" ]] && break
    echo "  Passwords do not match — try again."
done
# postgis:// keeps GeoDjango's DB backend; host "db" is the compose service.
DATABASE_URL="postgis://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"

# ── AWS (optional: S3 media + SES email) ──────────────────────────────────────
echo ""
echo "--- AWS: S3 media + SES email (optional) ---"
echo "S3 activates when a bucket is set; SES sends when keys are set and DEBUG=false."
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
AWS_STORAGE_BUCKET_NAME=""
AWS_S3_REGION_NAME="us-east-2"
printf "Configure AWS now? [y/N]: "
read -r aws_choice
if [[ "$aws_choice" =~ ^[Yy]$ ]]; then
    prompt          "AWS_ACCESS_KEY_ID"          AWS_ACCESS_KEY_ID
    prompt          "AWS_SECRET_ACCESS_KEY"      AWS_SECRET_ACCESS_KEY "" secret
    prompt_optional "AWS_STORAGE_BUCKET_NAME (blank = local filesystem)" AWS_STORAGE_BUCKET_NAME "waygon-bucket"
    prompt_optional "AWS_S3_REGION_NAME"         AWS_S3_REGION_NAME      "us-east-2"
fi
prompt_optional "DEFAULT_FROM_EMAIL" DEFAULT_FROM_EMAIL "noreply@${APEX}"

# ── Firebase (service-account key + optional extra env) ────────────────────────
# The mobile API verifies Firebase ID tokens with a service-account key. The key
# is a JSON *file* (git-ignored) that we copy into env/fbsvc.json; docker-compose
# mounts it into the containers at /app/env/fbsvc.json, which is what
# FIREBASE_CREDENTIALS points to below.
echo ""
echo "--- Firebase (service-account key for verifying mobile ID tokens) ---"
FIREBASE_CREDENTIALS="/app/env/fbsvc.json"   # in-container path (see docker-compose mount)

keep_existing=""
if [[ -f env/fbsvc.json ]]; then
    printf "env/fbsvc.json already exists. Replace it? [y/N]: "
    read -r fb_replace
    [[ "$fb_replace" =~ ^[Yy]$ ]] || { keep_existing="yes"; echo "  Keeping existing env/fbsvc.json."; }
fi

if [[ -z "$keep_existing" ]]; then
    while true; do
        prompt "Path to Firebase service-account JSON (copied into env/fbsvc.json)" FB_SRC
        FB_SRC="${FB_SRC/#\~/$HOME}"          # expand a leading ~
        if [[ ! -f "$FB_SRC" ]]; then
            echo "  No file at: $FB_SRC — try again."
            continue
        fi
        if ! python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$FB_SRC" 2>/dev/null; then
            echo "  Not valid JSON: $FB_SRC — try again."
            continue
        fi
        cp "$FB_SRC" env/fbsvc.json
        chmod 600 env/fbsvc.json
        echo "  Copied to env/fbsvc.json (mode 600)."
        break
    done
fi

# Any extra Firebase-related env vars (e.g. FIREBASE_PROJECT_ID). Optional and
# free-form so the file can carry whatever the project needs without code edits.
FIREBASE_EXTRA=""
printf "Add extra Firebase env vars? [y/N]: "
read -r fb_extra_choice
if [[ "$fb_extra_choice" =~ ^[Yy]$ ]]; then
    echo "Enter one KEY=VALUE per line; blank line to finish."
    while true; do
        printf "  > "
        read -r kv
        [[ -z "$kv" ]] && break
        if [[ "$kv" != *=* || "$kv" == =* ]]; then
            echo "    (expected KEY=VALUE — skipped)"
            continue
        fi
        FIREBASE_EXTRA+="${kv}"$'\n'
    done
fi

# ── First admin ───────────────────────────────────────────────────────────────
echo ""
echo "--- First admin (created on first container boot) ---"
prompt_optional "FIRST_ADMIN_USERNAME" FIRST_ADMIN_USERNAME "admin"
prompt          "FIRST_ADMIN_PASSWORD" FIRST_ADMIN_PASSWORD "" secret
prompt_optional "FIRST_ADMIN_EMAIL (optional)" FIRST_ADMIN_EMAIL ""

# ── write file ────────────────────────────────────────────────────────────────
cat > "$ENV_FILE" <<EOF
# Generated by bin/setup_env.sh — do not commit.

# --- Django ---
SECRET_KEY=${SECRET_KEY}
DEBUG=false
SITE_ADDRESS=${SITE_ADDRESS}
PROD_HOSTS=${PROD_HOSTS}
WEB_CONCURRENCY=${WEB_CONCURRENCY}
GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}

# --- Postgres ---
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
DATABASE_URL=${DATABASE_URL}

# --- AWS (S3 media + SES email; blank bucket = local filesystem) ---
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
AWS_STORAGE_BUCKET_NAME=${AWS_STORAGE_BUCKET_NAME}
AWS_S3_REGION_NAME=${AWS_S3_REGION_NAME}
DEFAULT_FROM_EMAIL=${DEFAULT_FROM_EMAIL}

# --- Firebase (service-account key mounted at this path; see docker-compose) ---
FIREBASE_CREDENTIALS=${FIREBASE_CREDENTIALS}
${FIREBASE_EXTRA}
# --- First admin ---
FIRST_ADMIN_USERNAME=${FIRST_ADMIN_USERNAME}
FIRST_ADMIN_PASSWORD=${FIRST_ADMIN_PASSWORD}
FIRST_ADMIN_EMAIL=${FIRST_ADMIN_EMAIL}
EOF

chmod 600 "$ENV_FILE"
echo ""
echo "Written to $ENV_FILE (mode 600)."

echo ""
echo "Next: 'make docker-deploy' to build and start the stack."
