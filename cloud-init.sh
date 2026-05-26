#!/bin/bash
# ============================================================================
# Already Here Command OS — Cloud-Init Runner
# ============================================================================
# Top-level wrapper invoked by OCI's cloud-init. The actual user-data field
# in OCI only needs TWO LINES (zero risk of paste-mangling):
#
#   #!/bin/bash
#   curl -fsSL https://raw.githubusercontent.com/Quantam101/already-here-dashboard/main/cloud-init.sh | bash
#
# This file does the heavy lifting:
#   1. Installs git, curl, ca-certificates
#   2. Calls scripts/oci-bootstrap.sh (which auto-detects RAM → SQLite mode)
#   3. Deploys WITHOUT secrets — operator SSHs in afterward to add them
#
# Cost: $0/month forever (Oracle Cloud Always Free + Let's Encrypt + Docker)
# ============================================================================
set -e
exec > /var/log/command-os-bootstrap.log 2>&1
echo "=== cloud-init started at $(date) ==="

# Wait for network + apt locks
sleep 30
apt-get update -qq
apt-get install -y -qq curl ca-certificates git

# These are intentionally EMPTY at first boot. After the stack is live,
# the operator SSHs in and edits /opt/command-os/backend/.env to add them:
#   EMERGENT_LLM_KEY  - get from Emergent → Profile → Universal Key
#   STRIPE_API_KEY    - sk_test_... or sk_live_... from dashboard.stripe.com
#   OPERATOR_EMAIL    - Google email that locks dashboard access
export EMERGENT_LLM_KEY=""
export STRIPE_API_KEY="sk_test_emergent"
export OPERATOR_EMAIL=""

# Fetch + run the real bootstrap. RAM auto-detect picks SQLite mode for <1500MB hosts.
curl -fsSL https://raw.githubusercontent.com/Quantam101/already-here-dashboard/main/scripts/oci-bootstrap.sh -o /tmp/bs.sh
bash /tmp/bs.sh \
  -d alreadyherellc.com \
  -e dispatch@alreadyherellc.com \
  -r https://github.com/Quantam101/already-here-dashboard.git

echo ""
echo "============================================================"
echo "BOOTSTRAP COMPLETE: $(date)"
echo "============================================================"
echo ""
echo "Next steps (do these via SSH once instance is reachable):"
echo "  1. ssh -i ~/.ssh/<your-key> ubuntu@<this-instance-ip>"
echo "  2. sudo nano /opt/command-os/backend/.env"
echo "     - Set EMERGENT_LLM_KEY=sk-emergent-..."
echo "     - Set OPERATOR_EMAIL=your@email.com"
echo "     - Optionally STRIPE_API_KEY=sk_live_..."
echo "  3. cd /opt/command-os"
echo "     sudo docker compose -f docker-compose.sqlite.yml restart backend"
echo "  4. Open https://alreadyherellc.com in browser"
echo ""
echo "Health: https://alreadyherellc.com/api/health/"
echo "Logs:   sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml logs -f"
