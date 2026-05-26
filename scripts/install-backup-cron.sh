#!/bin/bash
# Already Here Command OS — Install backup systemd timer
#
# One-shot installer. Run as root on the OCI host AFTER the bootstrap completes.
# Idempotent: re-runs replace prior unit files.
#
#   sudo bash /opt/command-os/scripts/install-backup-cron.sh
#
# What it does:
#   - Installs sqlite3 (apt) if missing
#   - Writes /etc/systemd/system/cmdos-backup.{service,timer}
#   - Enables + starts the timer (03:00 UTC nightly)
#   - Runs one backup immediately so you have a baseline file

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/command-os}"
BACKUP_SCRIPT="$APP_DIR/scripts/backup-sqlite.sh"
SERVICE_NAME="cmdos-backup"

if [ "$EUID" -ne 0 ]; then
  echo "Must be run as root. Try: sudo bash $0"
  exit 1
fi

if [ ! -x "$BACKUP_SCRIPT" ]; then
  chmod +x "$BACKUP_SCRIPT" 2>/dev/null || {
    echo "Backup script not found or unexecutable at $BACKUP_SCRIPT"
    exit 1
  }
fi

# 1) Ensure sqlite3 binary is available (for the .backup atomic snapshot)
if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "→ Installing sqlite3..."
  apt-get update -qq
  apt-get install -y -qq sqlite3
fi

# 2) Write the service unit (one-shot — runs the backup script and exits)
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Already Here Command OS — Nightly SQLite Backup
After=docker.service network-online.target
Wants=docker.service network-online.target

[Service]
Type=oneshot
User=root
Environment=APP_DIR=$APP_DIR
WorkingDirectory=$APP_DIR
ExecStart=$BACKUP_SCRIPT
StandardOutput=append:/var/log/cmdos-backup.log
StandardError=append:/var/log/cmdos-backup.log

[Install]
WantedBy=multi-user.target
EOF

# 3) Write the timer unit (fires daily at 03:00 UTC with 1h randomization)
cat > "/etc/systemd/system/${SERVICE_NAME}.timer" <<EOF
[Unit]
Description=Daily 03:00 UTC trigger for ${SERVICE_NAME}.service

[Timer]
OnCalendar=*-*-* 03:00:00 UTC
RandomizedDelaySec=1h
Persistent=true
Unit=${SERVICE_NAME}.service

[Install]
WantedBy=timers.target
EOF

# 4) Reload + enable
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}.timer"

# 5) Run one immediately to confirm wiring
echo "→ Running one backup now to confirm wiring..."
systemctl start "${SERVICE_NAME}.service" || true
sleep 2

echo ""
echo "============================================================"
echo "BACKUP CRON INSTALLED"
echo "============================================================"
echo "Timer status:    systemctl list-timers ${SERVICE_NAME}.timer"
echo "Service logs:    journalctl -u ${SERVICE_NAME}.service --since today"
echo "Script log:      tail -f /var/log/cmdos-backup.log"
echo "Backup dir:      $APP_DIR/backups"
echo ""
echo "Run manually any time:"
echo "  sudo systemctl start ${SERVICE_NAME}.service"
echo "============================================================"
