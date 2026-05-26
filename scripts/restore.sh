#!/bin/bash
# Already Here Command OS - Restore Script

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <backup-file.tar.gz>"
  echo "Available backups:"
  ls -lh /app/backups/command-os-backup-*.tar.gz 2>/dev/null || echo "  (none)"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "=== Command OS Restore ==="
echo "Source: $BACKUP_FILE"
echo "⚠️  This will REPLACE all current data!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

TEMP_DIR="/tmp/command-os-restore-$$"
mkdir -p "$TEMP_DIR"

echo "→ Extracting backup..."
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

echo "→ Restoring MongoDB..."
mongorestore --uri="${MONGO_URL:-mongodb://localhost:27017}" \
  --db="${DB_NAME:-test_database}" \
  --drop \
  "$TEMP_DIR/${DB_NAME:-test_database}" \
  --quiet

echo "→ Restoring exports..."
if [ -d "$TEMP_DIR/exports" ]; then
  cp -r "$TEMP_DIR/exports/." /app/exports/
fi

rm -rf "$TEMP_DIR"

echo "✓ Restore complete from $BACKUP_FILE"
echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"event\":\"restore.completed\",\"source\":\"$BACKUP_FILE\"}" >> /app/logs/backup.log
