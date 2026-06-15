#!/usr/bin/env bash
# Kill orphaned Django processes (runserver / db_worker / gunicorn) left behind
# by a previous `make server`, so a restart doesn't hit "address already in use".

# The [m]/[g] trick excludes the grep process itself from the match.
PIDS=$(ps aux | grep -E '[m]ain\.py (runserver|db_worker)|[m]anage\.py (runserver|db_worker)|[g]unicorn config\.asgi' | awk '{print $2}')

if [[ -n "$PIDS" ]]; then
  echo "$PIDS"
  # Gentle kill first.
  echo "$PIDS" | xargs -n1 kill 2>/dev/null
  sleep 0.5
  # Force kill anything that survived.
  REMAIN=$(echo "$PIDS" | xargs -n1 | while read -r p; do ps -p "$p" >/dev/null 2>&1 && echo "$p"; done)
  if [[ -n "$REMAIN" ]]; then
    echo "Force killing: $REMAIN"
    echo "$REMAIN" | xargs -n1 kill -9 2>/dev/null
  fi
else
  echo "No Django processes found."
fi

echo "Cleanup complete."
