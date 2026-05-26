#!/usr/bin/env bash
# Already Here Command OS — Pre-deploy validation
# Run this BEFORE oci-bootstrap.sh to catch mistakes early.
#
# Usage:  bash scripts/preflight.sh

set -u
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0

check_pass() { echo -e "  ${GREEN}✓${NC} $1"; PASS=$((PASS + 1)); }
check_fail() { echo -e "  ${RED}✗${NC} $1"; FAIL=$((FAIL + 1)); }
check_warn() { echo -e "  ${YELLOW}!${NC} $1"; WARN=$((WARN + 1)); }
section() { echo -e "\n${CYAN}■ $1${NC}"; }

cd "$(dirname "$0")/.."
ROOT=$(pwd)

section "Required deploy artifacts"
for f in docker-compose.yml Caddyfile DEPLOY-TO-OCI.md scripts/oci-bootstrap.sh backend/server.py backend/seed_data.py frontend/package.json; do
  if [ -f "$ROOT/$f" ]; then check_pass "$f"; else check_fail "MISSING: $f"; fi
done

section "Shell script syntax"
for s in scripts/oci-bootstrap.sh scripts/deploy-local.sh scripts/backup.sh scripts/healthcheck.sh scripts/validate-oci.sh; do
  if [ -f "$ROOT/$s" ]; then
    if bash -n "$ROOT/$s" 2>/dev/null; then check_pass "$s syntax OK"; else check_fail "$s syntax FAIL"; fi
  fi
done

section "docker-compose validates"
if command -v docker >/dev/null 2>&1; then
  if docker compose -f "$ROOT/docker-compose.yml" config >/dev/null 2>&1; then
    check_pass "docker-compose.yml valid"
  else
    check_fail "docker-compose.yml INVALID — run: docker compose config"
  fi
else
  check_warn "docker not installed locally (fine — only needed on OCI)"
fi

section "Caddyfile references the right domain"
if grep -q "alreadyherellc.com" "$ROOT/Caddyfile" 2>/dev/null; then
  check_pass "Caddyfile contains alreadyherellc.com"
else
  check_warn "Caddyfile does not mention alreadyherellc.com — bootstrap will regenerate it"
fi

section "Backend env keys referenced"
for k in MONGO_URL DB_NAME EMERGENT_LLM_KEY; do
  if grep -rq "$k" "$ROOT/backend" 2>/dev/null; then check_pass "$k used in backend code"; else check_warn "$k not referenced"; fi
done

section "Python imports cleanly"
if (cd "$ROOT/backend" && python -c "import server" 2>/dev/null); then
  check_pass "backend/server.py imports without error"
else
  check_fail "backend/server.py FAILS to import — fix before deploy"
fi

section "Tests pass"
if (cd "$ROOT" && python -m pytest backend/tests/ -q --tb=no 2>&1 | tail -1 | grep -q "passed"); then
  RESULT=$(cd "$ROOT" && python -m pytest backend/tests/ -q --tb=no 2>&1 | tail -1)
  check_pass "pytest: $RESULT"
else
  check_fail "pytest is failing — fix before deploy"
fi

section "Frontend build environment"
if [ -f "$ROOT/frontend/.env" ] && grep -q "REACT_APP_BACKEND_URL=" "$ROOT/frontend/.env"; then
  check_pass "frontend/.env has REACT_APP_BACKEND_URL"
else
  check_fail "frontend/.env missing REACT_APP_BACKEND_URL"
fi

section "Git repo state"
if [ -d "$ROOT/.git" ]; then
  BRANCH=$(git -C "$ROOT" branch --show-current 2>/dev/null || echo "?")
  UNCOMMITTED=$(git -C "$ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  REMOTE=$(git -C "$ROOT" remote get-url origin 2>/dev/null || echo "")
  check_pass "git branch: $BRANCH"
  if [ -n "$REMOTE" ]; then
    check_pass "git remote: $REMOTE"
  else
    check_warn "no git remote set — push to GitHub via Emergent 'Save to GitHub' button first"
  fi
  if [ "$UNCOMMITTED" = "0" ]; then
    check_pass "working tree clean"
  else
    check_warn "$UNCOMMITTED uncommitted change(s)"
  fi
else
  check_warn "not a git repo"
fi

section "Summary"
TOTAL=$((PASS + FAIL + WARN))
echo -e "  ${GREEN}Passed${NC}: $PASS  ${YELLOW}Warnings${NC}: $WARN  ${RED}Failed${NC}: $FAIL  (of $TOTAL checks)"
if [ "$FAIL" -gt 0 ]; then
  echo -e "\n${RED}DEPLOY BLOCKED${NC} — fix the failed checks before running oci-bootstrap.sh"
  exit 1
fi
if [ "$WARN" -gt 0 ]; then
  echo -e "\n${YELLOW}OK with warnings${NC} — review warnings then proceed with DEPLOY-TO-OCI.md"
else
  echo -e "\n${GREEN}READY TO DEPLOY${NC} — follow DEPLOY-TO-OCI.md from Step 1"
fi
exit 0
