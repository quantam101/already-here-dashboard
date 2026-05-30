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

# ── Step 0: Install operator SSH key (idempotent, runs FIRST) ──────────────
# OCI sometimes mangles long single-line keys in the "Paste public keys"
# textbox. This block guarantees the key is installed regardless.
OPERATOR_PUBKEY="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCc9bbH4rWxMbENW5DOBRm4+pw0Cb49mxU1eTbYt+HpEWIW7MM7dqtoIZE3zlaFvsbcJdbwB2togRYabMAU1r+UKp8IJ8OkE/4JD1ThR/W2b8Q81wAeHrNeSJLL0GlIZZD7q92XiZls7rfju/hDuWlJOHZWY1Zdk+dIZ6hmM6IHtWhiZqtSPXs7kanXTmJxbbnW4KVT7Oa6oKHDrwNSgiMsf7Yy2axn5QWUBqvWlASgP9BfNmt3qB+8ZZOL6aCOb2w/8SH/oqPh4hdMzKaDYd9llLsWCcc3gpfXslMX/+Ac0cMkTxTpfci1aw5Ls9as9SRuD1BrDQLBoJOuY6vYZrLlJQ3Ln4LEy+mbo+df3vF7NxLuyXrScnDywYH5zfmXPrsQqADZyGfuzVDOgEEC0JOHnia0lPmeXJftK37iMAvofWUMc4TGolW3Hpbv+aLUJXt+DUCl9ykKMX7s+SK49lBjgH1QWk2ILVrE8LIrh12RsNHrDSOGeBbMCA4TEnBG+Gx+bM7NqiGV9uwcoW+QWB/Wh5Az/FPQElgSKTKUOb1ZyNPvVMXWyxY4UmjdXoZbLLV+iUnK74ZsK+U5p0OsckS4975qLv2/YRLjd9Tv4XjrpFhDxY8FmG52WYprUhD313WLnSeWvrfYlJI8tU9DehkkkHbwnG69QCswB0GNaKVxqw== cmdos@cloudshell"

mkdir -p /home/ubuntu/.ssh
touch /home/ubuntu/.ssh/authorized_keys
if ! grep -q "cmdos@cloudshell" /home/ubuntu/.ssh/authorized_keys 2>/dev/null; then
  echo "$OPERATOR_PUBKEY" >> /home/ubuntu/.ssh/authorized_keys
fi
chmod 700 /home/ubuntu/.ssh
chmod 600 /home/ubuntu/.ssh/authorized_keys
chown -R ubuntu:ubuntu /home/ubuntu/.ssh
echo "=== SSH key installed for ubuntu@ ==="

# ── Step 1: Wait for network + install base packages ───────────────────────
sleep 30
apt-get update -qq
apt-get install -y -qq curl ca-certificates git

# These are intentionally EMPTY at first boot. After the stack is live,
# the operator SSHs in and edits /opt/command-os/backend/.env to add them:
#   LLM_API_KEY      - Google AI Studio / Anthropic / OpenAI key (routed via litellm)
#   STRIPE_API_KEY   - sk_test_... or sk_live_... from dashboard.stripe.com
#   OPERATOR_EMAIL   - email that locks dashboard access (allowlist)
#   OPERATOR_TOKEN   - long random string for local auth (openssl rand -hex 32)
export LLM_API_KEY=""
export STRIPE_API_KEY=""  # Set to sk_live_... after SSHing in; empty = Stripe mock mode
export OPERATOR_EMAIL=""
export OPERATOR_TOKEN=""
export AUTONOMY_LEVEL="L3"
export DUAL_ACTOR_APPROVAL="false"

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
echo "     - Set LLM_API_KEY=<your provider key>"
echo "     - Set OPERATOR_EMAIL=your@email.com"
echo "     - Set OPERATOR_TOKEN=\$(openssl rand -hex 32)"
echo "     - Optionally STRIPE_API_KEY=sk_live_..."
echo "  3. cd /opt/command-os"
echo "     sudo docker compose -f docker-compose.sqlite.yml restart backend"
echo "  4. Open https://alreadyherellc.com in browser"
echo ""
echo "Health: https://alreadyherellc.com/api/health/"
echo "Logs:   sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml logs -f"
