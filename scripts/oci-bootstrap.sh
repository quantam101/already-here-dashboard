#!/usr/bin/env bash
# ============================================================================
# Already Here Command OS - ONE-COMMAND OCI ALWAYS FREE DEPLOYER
# ============================================================================
# Run this on a fresh Oracle Cloud Always Free Compute instance (Ubuntu 22.04+
# ARM Ampere A1 or VM.Standard.E2.1.Micro). Installs Docker, clones the repo,
# wires env, and brings the stack up under Caddy with auto HTTPS.
#
#   curl -fsSL https://raw.githubusercontent.com/<YOU>/<REPO>/main/scripts/oci-bootstrap.sh | sudo bash -s -- \
#     -d your-domain.com -e you@you.com -r https://github.com/<YOU>/<REPO>.git
#
#   FLAGS:
#     -d <domain>    Your domain (DNS A-record must point to this server's public IP)
#     -e <email>     Email for Let's Encrypt
#     -r <repo_url>  Git clone URL
#     -m <mongo>     OPTIONAL external MongoDB URL (defaults to local docker mongo)
# ============================================================================
set -euo pipefail

DOMAIN=""; EMAIL=""; REPO=""; MONGO=""
while getopts "d:e:r:m:h" opt; do
  case $opt in
    d) DOMAIN="$OPTARG" ;;
    e) EMAIL="$OPTARG" ;;
    r) REPO="$OPTARG" ;;
    m) MONGO="$OPTARG" ;;
    h) sed -n '1,/^# ====/p' "$0"; exit 0 ;;
    \?) echo "Invalid -$OPTARG" >&2; exit 1 ;;
  esac
done

[ -z "$DOMAIN" ] || [ -z "$EMAIL" ] || [ -z "$REPO" ] && {
  echo "Usage: sudo bash oci-bootstrap.sh -d DOMAIN -e EMAIL -r REPO_URL [-m EXTERNAL_MONGO]" >&2
  exit 1
}

log()  { echo -e "\033[0;32m[bootstrap]\033[0m $*"; }
warn() { echo -e "\033[1;33m[bootstrap]\033[0m $*"; }
err()  { echo -e "\033[0;31m[bootstrap]\033[0m $*" >&2; }

[ "$(id -u)" -ne 0 ] && err "Must run as root (sudo)" && exit 1

log "1/6  apt update + base packages..."
apt-get update -qq
apt-get install -y -qq curl ca-certificates git ufw

log "2/6  installing Docker + Compose v2..."
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
if ! docker compose version >/dev/null 2>&1; then
  apt-get install -y -qq docker-compose-plugin
fi
systemctl enable docker --now

log "3/6  opening firewall (80, 443)..."
ufw allow OpenSSH || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
ufw --force enable || true

# OCI also blocks inbound by default at the VNIC level - the user MUST also
# add ingress rules in OCI Networking → Security Lists for ports 80 + 443.
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

log "5/6  writing .env files..."
cat > backend/.env <<EOF
MONGO_URL="${MONGO:-mongodb://mongodb:27017}"
DB_NAME="command_os"
CORS_ORIGINS="https://${DOMAIN}"
EMERGENT_LLM_KEY="${EMERGENT_LLM_KEY:-}"
STRIPE_API_KEY="${STRIPE_API_KEY:-sk_test_emergent}"
STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-}"
OPERATOR_EMAIL="${OPERATOR_EMAIL:-${EMAIL}}"
BW_SESSION="${BW_SESSION:-}"
ZERO_SPEND_MODE=true
EOF
cat > frontend/.env <<EOF
REACT_APP_BACKEND_URL="https://${DOMAIN}"
EOF
cat > Caddyfile <<EOF
${DOMAIN} {
    encode gzip
    handle /api/* {
        reverse_proxy backend:8001
    }
    handle {
        reverse_proxy frontend:80
    }
    tls ${EMAIL}
}
EOF

log "6/6  docker compose up -d..."
docker compose pull mongo 2>/dev/null || true
docker compose up -d --build

log ""
log "============================================================"
log "  Deployment started. Logs: docker compose logs -f"
log "  Health: https://${DOMAIN}/api/health"
log "  After DNS A-record propagates, Caddy issues HTTPS automatically."
log "============================================================"
log "Cost: \$0/month (OCI Always Free + Let's Encrypt + Docker)"
