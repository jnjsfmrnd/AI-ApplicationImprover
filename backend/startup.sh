#!/bin/bash
set -e

# Ensure the persistent data directory exists (Azure App Service /home is Azure Files)
mkdir -p /home/data

# Run any pending database migrations
cd /home/site/wwwroot
python -m alembic upgrade head

# Start the FastAPI server; Azure injects $PORT (default 8000)
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --app-dir /home/site/wwwroot
