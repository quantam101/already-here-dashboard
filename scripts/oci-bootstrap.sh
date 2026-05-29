#!/usr/bin/env bash
# ============================================================================
# Already Here Command OS - ONE-COMMAND OCI ALWAYS FREE DEPLOYER
# ============================================================================
# Run this on a fresh Oracle Cloud Always Free Compute instance (Ubuntu 22.04+).
#
# Auto-detects RAM: hosts with <= 1.5 GB use the SQLite/static-frontend stack
# (docker-compose.sqlite.yml). Larger hosts use the MongoDB stack.
#
#   curl -fsSL https://raw.githubusercontent.com/<YOU>/<REPO>/main/scripts/oci-bootstrap.sh | sudo bash -s -- \
#     -d your-domain.com -e you@you.com -r https://github.com/<YOU>/<REPO>.git
#
#   FLAGS:
#     -d <domain>    Your domain (DNS A-record must point to this server's public IP)
#     -e <email>     Email for Let's Encrypt
#     -r <repo_url>  Git clone URL
#     -m <mongo>     OPTIONAL external MongoDB URL (defaults to local docker mongo)
#     -b <backend>   FORCE 'sqlite' or 'mongodb' (overrides auto-detect)
#     -w <worker>    OPTIONAL profitengine-server URL for heavy-job offload
# ============================================================================
set -euo pipefail

DOMAIN=""; EMAIL=""; REPO=""; MONGO=""; FORCE_BACKEND=""; WORKER_URL=""
while getopts "d:e:r:m:b:w:h" opt; do
  case $opt in
    d) DOMAIN="$OPTARG" ;;
    e) EMAIL="$OPTARG" ;;
    r) REPO="$OPTARG" ;;
    m) MONGO="$OPTARG" ;;
    b) FORCE_BACKEND="$OPTARG" ;;
    w) WORKER_URL="$OPTARG" ;;
    h) sed -n '1,/^# ====/p' "$0"; exit 0 ;;
    \?) echo "Invalid -$OPTARG" >&2; exit 1 ;;
  esac
done

[ -z "$DOMAIN" ] || [ -z "$EMAIL" ] || [ -z "$REPO" ] && {
  echo "Usage: sudo bash oci-bootstrap.sh -d DOMAIN -e EMAIL -r REPO_URL [-m EXTERNAL_MONGO] [-b sqlite|mongodb] [-w WORKER_URL]" >&2
  exit 1
}

log()  { echo -e "\033[0;32m[bootstrap]\033[0m $*"; }
warn() { echo -e "\033[1;33m[bootstrap]\033[0m $*"; }
err()  { echo -e "\033[0;31m[bootstrap]\033[0m $*" >&2; }

[ "$(id -u)" -ne 0 ] && err "Must run as root (sudo)" && exit 1

# Decide backend based on RAM (or honor explicit override)
RAM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
if [ -n "$FORCE_BACKEND" ]; then
  BACKEND="$FORCE_BACKEND"
elif [ "$RAM_MB" -lt 1500 ]; then
  BACKEND="sqlite"
  log "Detected ${RAM_MB} MB RAM (< 1500 MB) → using SQLite/static-frontend mode (Free-Only Build Directive compliant)"
else
  BACKEND="mongodb"
  log "Detected ${RAM_MB} MB RAM (>= 1500 MB) → using MongoDB mode"
fi
COMPOSE_FILE="docker-compose.yml"
[ "$BACKEND" = "sqlite" ] && COMPOSE_FILE="docker-compose.sqlite.yml"

log "1/6  apt update + base packages..."
apt-get update -qq
apt-get install -y -qq curl ca-certificates git ufw

log "2/6  installing Docker + Compose v2..."
if ! command -v docker >/dev/null 2>&1; then
  # Install Docker manually — the official get.docker.com script tries to
  # install docker-model-plugin which doesn't exist for Ubuntu 20.04 (focal).
  # We install only the packages that actually exist.
  apt-get install -y -qq ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    curl -fsSL "https://download.docker.com/linux/ubuntu/gpg" -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
  fi
  CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  # Install only required packages — skip docker-model-plugin (missing on focal)
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin
fi
systemctl enable docker --now

log "3/6  opening firewall (80, 443)..."
ufw allow OpenSSH || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
ufw --force enable || true
warn "OCI Security List rules: add ingress for tcp/80 and tcp/443 in the OCI Console"

log "3b/6  installing Bitwarden CLI (optional - skipped on failure)..."
if ! command -v bw >/dev/null 2>&1; then
  ( set -e
    apt-get install -y -qq unzip
    curl -fL "https://vault.bitwarden.com/download/?app=cli&platform=linux" -o /tmp/bw.zip
    unzip -o /tmp/bw.zip -d /usr/local/bin/
    chmod +x /usr/local/bin/bw
    rm -f /tmp/bw.zip
  ) && log "bw CLI installed: $(bw --version 2>/dev/null || echo n/a)" \
    || warn "bw CLI install skipped (offline / arch mismatch). Run later: see /secrets page in dashboard."
fi

log "4/6  cloning repo to /opt/command-os..."
mkdir -p /opt
[ -d /opt/command-os ] || git clone "$REPO" /opt/command-os
cd /opt/command-os
git pull --ff-only || true

log "5/6  writing .env files (backend=${BACKEND})..."
cat > backend/.env <<EOF
STORAGE_BACKEND="${BACKEND}"
SQLITE_PATH="/app/data/command_os.db"
MONGO_URL="${MONGO:-mongodb://mongodb:27017}"
DB_NAME="command_os"
CORS_ORIGINS="https://${DOMAIN}"
LLM_API_KEY="${LLM_API_KEY:-${EMERGENT_LLM_KEY:-}}"
STRIPE_API_KEY="${STRIPE_API_KEY:-sk_test_placeholder}"
STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-}"
OPERATOR_EMAIL="${OPERATOR_EMAIL:-${EMAIL}}"
OPERATOR_TOKEN="${OPERATOR_TOKEN:-}"
AUTONOMY_LEVEL="${AUTONOMY_LEVEL:-L3}"
DUAL_ACTOR_APPROVAL="${DUAL_ACTOR_APPROVAL:-false}"
BW_SESSION="${BW_SESSION:-}"
WORKER_BASE_URL="${WORKER_URL}"
ZERO_SPEND_MODE=true
EOF
cat > frontend/.env <<EOF
REACT_APP_BACKEND_URL="https://${DOMAIN}"
EOF

if [ "$BACKEND" = "sqlite" ]; then
  # SQLite + static frontend path - pre-build the React bundle on host
  log "5b/6  building React static bundle (one-time, ~3 min)..."
  if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
    npm install -g yarn
  fi
  (cd frontend && yarn install --frozen-lockfile && CI=true yarn build)
  log "Static bundle built: $(du -sh frontend/build 2>/dev/null | cut -f1)"
else
  # MongoDB stack uses live Caddy + per-domain config
  cat > Caddyfile <<EOF
${DOMAIN} {
    encode gzip
    handle /api/* {
        reverse_proxy backend:8001
    }
    handle {
        reverse_proxy frontend:3000
    }
    tls ${EMAIL}
}
EOF
fi

log "6/6  docker compose up -d (using ${COMPOSE_FILE})..."
DOMAIN="${DOMAIN}" docker compose -f "${COMPOSE_FILE}" up -d --build

if [ "$BACKEND" = "sqlite" ]; then
  log "5c/6  seeding SQLite database..."
  sleep 5
  docker compose -f "${COMPOSE_FILE}" exec -T backend python seed_data.py || warn "seed failed - run manually later: docker compose -f ${COMPOSE_FILE} exec backend python seed_data.py"
fi

log ""
log "============================================================"
log "  Deployment started. Logs: docker compose -f ${COMPOSE_FILE} logs -f"
log "  Backend mode: ${BACKEND}"
log "  Health: https://${DOMAIN}/api/health"
log "  After DNS A-record propagates, Caddy issues HTTPS automatically."
log "============================================================"
log "Cost: \$0/month (OCI Always Free + Let's Encrypt + Docker)"
