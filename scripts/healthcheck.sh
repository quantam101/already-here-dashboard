#!/bin/bash
# Already Here Command OS - Health Check Script
# Validates all services and reports cost compliance

set -e

API_URL="${API_URL:-http://localhost:8001}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

echo "=== Command OS Health Check ==="
echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0

check() {
  local name="$1"
  local cmd="$2"

  printf "%-30s " "$name:"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "✓ OK"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
  else
    echo "✗ FAIL"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
  fi
}

# Service checks
check "MongoDB"        "mongosh --eval 'db.adminCommand({ping:1})' --quiet"
check "Backend API"    "curl -sf $API_URL/api/health/"
check "Frontend"       "curl -sf -o /dev/null $FRONTEND_URL"
check "Revenue API"    "curl -sf $API_URL/api/revenue/"
check "Agents API"     "curl -sf $API_URL/api/agents/"
check "Builds API"     "curl -sf $API_URL/api/builds/"
check "Studio API"     "curl -sf $API_URL/api/studio/connectors/"
check "Audit API"      "curl -sf $API_URL/api/audit/"

echo ""
echo "=== Cost Compliance Check ==="

# Check connector cost classes
CONNECTORS=$(curl -sf "$API_URL/api/studio/connectors/" 2>/dev/null || echo "[]")
FREE=$(echo "$CONNECTORS" | python3 -c "import sys,json;d=json.load(sys.stdin);print(len([c for c in d if c['cost_class'].startswith('free')]))" 2>/dev/null || echo "0")
MANUAL=$(echo "$CONNECTORS" | python3 -c "import sys,json;d=json.load(sys.stdin);print(len([c for c in d if c['cost_class']=='manual_free']))" 2>/dev/null || echo "0")
PAID_BLOCKED=$(echo "$CONNECTORS" | python3 -c "import sys,json;d=json.load(sys.stdin);print(len([c for c in d if c['cost_class']=='paid_blocked']))" 2>/dev/null || echo "0")

echo "Free connectors: $FREE"
echo "Manual export: $MANUAL"
echo "Paid blocked: $PAID_BLOCKED (Cost Guard active)"
echo "Monthly cost target: \$0"
echo ""

# Disk usage
echo "=== Resource Usage ==="
df -h / | awk 'NR==2 {printf "Disk usage: %s (%s used)\n", $5, $3}'
free -h | awk '/^Mem:/ {printf "Memory: %s used / %s total\n", $3, $2}'

# Summary
echo ""
echo "=== Summary ==="
echo "Checks passed: $CHECKS_PASSED"
echo "Checks failed: $CHECKS_FAILED"

if [ $CHECKS_FAILED -eq 0 ]; then
  echo "✓ All systems operational"
  exit 0
else
  echo "✗ Some checks failed"
  exit 1
fi
