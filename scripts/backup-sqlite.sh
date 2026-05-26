#!/bin/bash
# Already Here Command OS — SQLite Backup
#
# Backs up the production SQLite DB + the /app/backups directory mounted into
# the backend container. Designed to be called by the systemd timer installed
# via scripts/install-backup-cron.sh (runs nightly at 03:00 UTC).
#
# Idempotent. Safe to run manually any time.
# Cost: $0/month (uses host disk; no S3 dependency).

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/command-os}"
DB_PATH="${DB_PATH:-$APP_DIR/data/command_os.db}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/cmdos-sqlite-$TIMESTAMP.tar.gz"

echo "=== Command OS SQLite Backup ==="
echo "Timestamp(UTC): $TIMESTAMP"
echo "DB path: $DB_PATH"
echo "Backup dir: $BACKUP_DIR"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
  echo "✗ DB file not found at $DB_PATH — is the stack running in SQLite mode?"
  exit 1
fi

# 1) Quiesce the DB with sqlite3's atomic .backup command (works while running)
TMP="/tmp/cmdos-sqlite-$TIMESTAMP.db"
sqlite3 "$DB_PATH" ".backup '$TMP'" || {
  echo "✗ sqlite3 .backup failed — falling back to cp (may be inconsistent)"
  cp "$DB_PATH" "$TMP"
}

# 2) Tar the snapshot + any export packs
tar -czf "$BACKUP_FILE" -C "$(dirname "$TMP")" "$(basename "$TMP")" \
  $(test -d "$APP_DIR/exports" && echo "-C $APP_DIR exports") 2>/dev/null || \
  tar -czf "$BACKUP_FILE" -C "$(dirname "$TMP")" "$(basename "$TMP")"

rm -f "$TMP"

# 3) Retention
find "$BACKUP_DIR" -name "cmdos-sqlite-*.tar.gz" -mtime +"$RETENTION_DAYS" -delete

# 4) Report
SIZE="$(du -h "$BACKUP_FILE" | cut -f1)"
COUNT="$(ls -1 "$BACKUP_DIR"/cmdos-sqlite-*.tar.gz 2>/dev/null | wc -l)"
echo "✓ Backup: $BACKUP_FILE ($SIZE)"
echo "✓ Retained: $COUNT backups in $BACKUP_DIR (older than $RETENTION_DAYS days pruned)"
