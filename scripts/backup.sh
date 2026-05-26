#!/bin/bash
# Already Here Command OS - Backup Script
# Free local backups for OCI Always Free
# Backs up MongoDB database + content exports to /app/backups

set -e

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/command-os-backup-$TIMESTAMP.tar.gz"

echo "=== Command OS Backup ==="
echo "Timestamp: $TIMESTAMP"
echo "Backup dir: $BACKUP_DIR"

mkdir -p "$BACKUP_DIR"

# 1. Dump MongoDB
echo "→ Dumping MongoDB..."
TEMP_DUMP="/tmp/command-os-mongo-$TIMESTAMP"
mongodump --uri="${MONGO_URL:-mongodb://localhost:27017}" \
  --db="${DB_NAME:-test_database}" \
  --out="$TEMP_DUMP" \
  --quiet

# 2. Create tarball with mongo dump + exports + logs
echo "→ Creating archive..."
tar -czf "$BACKUP_FILE" \
  -C "$TEMP_DUMP" . \
  -C /app exports/ 2>/dev/null || true

# 3. Cleanup temp
rm -rf "$TEMP_DUMP"

# 4. Cleanup old backups
echo "→ Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "command-os-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete

# 5. Report
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
TOTAL_BACKUPS=$(ls -1 "$BACKUP_DIR"/command-os-backup-*.tar.gz 2>/dev/null | wc -l)

echo "✓ Backup complete: $BACKUP_FILE ($BACKUP_SIZE)"
echo "✓ Total backups in $BACKUP_DIR: $TOTAL_BACKUPS"

# Log to audit trail
echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"event\":\"backup.completed\",\"file\":\"$BACKUP_FILE\",\"size\":\"$BACKUP_SIZE\"}" >> /app/logs/backup.log
