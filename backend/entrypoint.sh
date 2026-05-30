#!/bin/bash
# Ensure data directories are writable by appuser
# (Docker named volumes can mount as root on first use)
if [ -d /app/data ] && [ ! -w /app/data ]; then
    echo "Fixing /app/data ownership..."
fi
mkdir -p /app/data /app/exports /app/logs
exec uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1
