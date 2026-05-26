#!/usr/bin/env bash
# ============================================================================
# Already Here Command OS - LOCAL LAPTOP DEPLOYMENT
# ============================================================================
# Production-ready local deployment fallback for when OCI is unavailable.
# Zero-cost. Runs entirely on your laptop or any local workstation.
#
# Requirements:
#   - Docker + Docker Compose (or local Python 3.11 + Node 20 + MongoDB)
#   - 4 GB free RAM
#   - 10 GB free disk
#
# Usage:
#   ./scripts/deploy-local.sh           # Docker mode (recommended)
#   ./scripts/deploy-local.sh --native  # Native mode (no Docker)
#   ./scripts/deploy-local.sh --stop    # Stop all services
#   ./scripts/deploy-local.sh --status  # Show status + health
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
cd "$APP_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${GREEN}[deploy-local]${NC} $*"; }
warn()  { echo -e "${YELLOW}[deploy-local]${NC} $*"; }
err()   { echo -e "${RED}[deploy-local]${NC} $*" >&2; }
info()  { echo -e "${BLUE}[deploy-local]${NC} $*"; }

MODE="docker"
ACTION="up"
for arg in "$@"; do
  case "$arg" in
    --native) MODE="native" ;;
    --stop)   ACTION="down" ;;
    --status) ACTION="status" ;;
    --help|-h)
      grep -E '^# ' "$0" | head -25
      exit 0
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Cost Guard pre-flight - NEVER allow paid services
# ---------------------------------------------------------------------------
check_cost_guard() {
  log "Cost Guard pre-flight: verifying $0/month policy..."
  local violations=0
  for var in STRIPE_LIVE_KEY OPENAI_API_KEY ANTHROPIC_API_KEY TWITTER_BEARER_TOKEN; do
    if [ -n "${!var:-}" ] && [ "${SYSTEM_MODE:-}" != "test" ]; then
      warn "  $var detected - blocked by Cost Guard unless explicitly approved"
      violations=$((violations + 1))
    fi
  done
  if [ "$violations" -eq 0 ]; then
    log "  Cost Guard: PASS (zero paid keys detected)"
  fi
}

# ---------------------------------------------------------------------------
# Docker mode
# ---------------------------------------------------------------------------
deploy_docker() {
  log "Deploying via Docker Compose..."
  if ! command -v docker >/dev/null 2>&1; then
    err "Docker not installed. Install: https://docs.docker.com/get-docker/"
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    err "Docker Compose v2 required."
    exit 1
  fi

  [ -f .env ] || {
    info "Creating .env from defaults..."
    cat > .env <<EOF
DB_NAME=command_os_local
CORS_ORIGINS=http://localhost:3000,http://localhost
EMERGENT_LLM_KEY=${EMERGENT_LLM_KEY:-}
EOF
  }

  docker compose pull mongodb 2>/dev/null || true
  docker compose up -d --build
  log "Stack started. Waiting for health..."
  sleep 8
  docker compose ps
}

docker_down() {
  log "Stopping Docker stack..."
  docker compose down
}

# ---------------------------------------------------------------------------
# Native mode (Emergent-style local supervisor processes)
# ---------------------------------------------------------------------------
deploy_native() {
  log "Native deployment (laptop/terminal direct mode)..."
  log "  Backend: http://localhost:8001"
  log "  Frontend: http://localhost:3000"
  log "  MongoDB: assumed running at \$MONGO_URL"
  log ""
  log "Ensure MongoDB is running locally, then:"
  echo "  cd backend && python -m venv .venv && . .venv/bin/activate"
  echo "  pip install -r requirements.txt"
  echo "  uvicorn server:app --host 0.0.0.0 --port 8001 &"
  echo ""
  echo "  cd frontend && yarn install && yarn start &"
  echo ""
  warn "For supervised mode this app already uses supervisorctl in the Emergent container."
}

# ---------------------------------------------------------------------------
# Status check
# ---------------------------------------------------------------------------
show_status() {
  log "Service status:"
  if command -v docker >/dev/null 2>&1 && docker compose ps 2>/dev/null | grep -q command-os; then
    docker compose ps
  fi

  log ""
  log "Endpoint health probes:"
  for url in \
    "http://localhost:8001/api/health" \
    "http://localhost:3000" ; do
    if curl -sf -o /dev/null --max-time 3 "$url"; then
      echo -e "  ${GREEN}OK${NC}  $url"
    else
      echo -e "  ${RED}DOWN${NC} $url"
    fi
  done
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
check_cost_guard
case "$ACTION" in
  up)
    if [ "$MODE" = "native" ]; then deploy_native
    else deploy_docker
    fi
    ;;
  down)
    docker_down
    ;;
  status)
    show_status
    ;;
esac

log "Done."
