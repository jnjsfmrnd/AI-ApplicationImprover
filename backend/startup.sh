#!/bin/bash
set -e

# Ensure the persistent data directory exists (Azure App Service /home is Azure Files)
mkdir -p /home/data

# Resolve the extracted app directory at runtime. Oryx may run the app from /tmp rather than /home/site/wwwroot.
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$APP_DIR/antenv"

cd "$APP_DIR"

# Run any pending database migrations using the venv Python directly
"$VENV/bin/python" -m alembic upgrade head

# Start the FastAPI server; Azure injects $PORT (default 8000)
exec "$VENV/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
