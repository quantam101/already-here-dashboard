"""Run a parallel SQLite-backed instance of the API for testing.

Listens on 127.0.0.1:8002 (separate from the live preview on 8001).
Uses an in-memory-ish file under /tmp so it can be wiped per run.
"""
import os
import sys

# Force SQLite mode BEFORE the server module imports
os.environ["STORAGE_BACKEND"] = "sqlite"
os.environ["SQLITE_PATH"] = "/tmp/command_os_test.db"

# Clear any stale db
db_path = "/tmp/command_os_test.db"
if os.path.exists(db_path):
    os.remove(db_path)

# Seed env vars expected by server
os.environ.setdefault("MONGO_URL", "unused")
os.environ.setdefault("DB_NAME", "command_os_test")
os.environ.setdefault("CORS_ORIGINS", "*")

sys.path.insert(0, "/app/backend")

import uvicorn
from server import app  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
