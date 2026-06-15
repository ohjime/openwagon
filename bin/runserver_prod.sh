#!/usr/bin/env bash
# Runtime entrypoint for the production container.
#   1. Apply migrations (incl. CREATE EXTENSION postgis + cache/task tables)
#   2. Ensure the database cache table exists
#   3. Create the first admin from FIRST_ADMIN_* (if provided)
#   4. Start gunicorn + the background task worker via Honcho (procfile.prod)
set -e

# Run from src/server regardless of how we were invoked.
cd "$(dirname "$0")/../src/server"

echo "🔄 Applying migrations..."
uv run --no-sync src/main.py migrate --noinput

echo "🗄️  Ensuring cache table..."
uv run --no-sync src/main.py createcachetable

echo "👤 Ensuring admin user..."
uv run --no-sync src/main.py shell <<'PYEOF'
import os

from django.contrib.auth import get_user_model

User = get_user_model()
email = os.getenv("FIRST_ADMIN_EMAIL", "").strip("'\"")
username = os.getenv("FIRST_ADMIN_USERNAME", "").strip("'\"")
password = os.getenv("FIRST_ADMIN_PASSWORD", "").strip("'\"")

if not (username and password):
    print("• FIRST_ADMIN_USERNAME / FIRST_ADMIN_PASSWORD not set — skipping admin creation.")
elif User.objects.filter(username=username).exists():
    print(f"• Admin '{username}' already exists.")
else:
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"✓ Created superuser '{username}'.")
PYEOF

echo "🚀 Starting gunicorn + worker via honcho..."
exec uv run --no-sync honcho -f procfile.prod start
