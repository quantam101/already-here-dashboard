#!/bin/bash
# Already Here Command OS - OCI Always Free Deployment Script
# Validates zero-cost configuration before deployment

set -e

echo "=== OCI Always Free Deployment Validator ==="
echo ""

# Check we're not using paid resources
echo "→ Validating Always Free compatibility..."

# Required tools
for tool in docker docker-compose curl python3; do
  if ! command -v "$tool" &> /dev/null; then
    echo "✗ Missing required tool: $tool"
    exit 1
  fi
done
echo "✓ Required tools installed"

# Check env file exists
if [ ! -f /app/backend/.env ]; then
  echo "✗ Missing /app/backend/.env"
  echo "  Required: MONGO_URL, DB_NAME, LLM_API_KEY"
  exit 1
fi

if [ ! -f /app/frontend/.env ]; then
  echo "✗ Missing /app/frontend/.env"
  echo "  Required: REACT_APP_BACKEND_URL"
  exit 1
fi

echo "✓ Environment files present"

# Verify Bitwarden CLI (optional but recommended)
if command -v bw &> /dev/null; then
  echo "✓ Bitwarden CLI installed"
else
  echo "⚠ Bitwarden CLI not installed (optional)"
  echo "  Install: npm install -g @bitwarden/cli"
fi

# Validate cost guard mode in env
if grep -q "ZERO_SPEND_MODE=true" /app/backend/.env; then
  echo "✓ Zero-spend mode enabled"
else
  echo "✗ ZERO_SPEND_MODE must be 'true' in backend/.env"
  exit 1
fi

# Check disk space (Always Free has 200GB total)
AVAILABLE_GB=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAILABLE_GB" -lt 5 ]; then
  echo "✗ Insufficient disk space ($AVAILABLE_GB GB available, 5 GB minimum)"
  exit 1
fi
echo "✓ Disk space: $AVAILABLE_GB GB available"

# Validate that no paid APIs are configured
if grep -E "(OPENAI|ANTHROPIC|STRIPE|TWILIO|SENDGRID).*KEY" /app/backend/.env | grep -v "^#" | grep -v "^LLM_API_KEY" > /dev/null 2>&1; then
  echo "⚠ Warning: Paid API keys detected in .env"
  echo "  Make sure Cost Guard blocks all paid actions"
fi

echo ""
echo "✓ All validation checks passed"
echo ""
echo "Next steps:"
echo "  1. Run: docker-compose up -d"
echo "  2. Or:  pm2 start ecosystem.config.js"
echo "  3. Setup HTTPS: docker-compose up -d caddy"
echo "  4. Verify: bash /app/scripts/healthcheck.sh"
echo ""
echo "Target operating cost: \$0/month"
