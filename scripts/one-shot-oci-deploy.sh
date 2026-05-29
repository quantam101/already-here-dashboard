#!/usr/bin/env bash
# Already Here Command OS — single-paste OCI bootstrap command
# =============================================================
# Pre-filled with the values the operator confirmed:
#   domain: alreadyherellc.com
#   email:  dispatch@alreadyherellc.com
#
# AFTER you SSH into your OCI Ubuntu 22.04 host as `ubuntu`, just paste this
# whole block. It will:
#   1. install curl + git (idempotent)
#   2. fetch the bootstrap script
#   3. run it with the right flags
#
# YOU MUST REPLACE THE GITHUB_REPO PLACEHOLDER on the line below with your
# actual repo URL once you have pushed via the "Save to GitHub" button.
#
# Then EVERY env var (LLM_API_KEY, STRIPE_API_KEY, OPERATOR_TOKEN) gets typed
# directly into backend/.env via `sudo nano` AFTER this finishes — NEVER paste
# secrets in chat or in this file.
# =============================================================

set -euo pipefail

GITHUB_REPO="https://github.com/<YOUR-USERNAME>/<YOUR-REPO>.git"   # ← edit me
DOMAIN="alreadyherellc.com"
EMAIL="dispatch@alreadyherellc.com"

if [[ "$GITHUB_REPO" == *"<YOUR-USERNAME>"* ]]; then
  echo "ERROR: edit GITHUB_REPO in this script first" >&2
  exit 1
fi

sudo apt-get update -y -qq
sudo apt-get install -y -qq curl ca-certificates git

# Fetch + run the real bootstrap. Auto-detects RAM and picks the right backend.
sudo bash <(curl -fsSL "$(echo "$GITHUB_REPO" | sed -E 's#\.git$##;s#github\.com#raw.githubusercontent.com#')/main/scripts/oci-bootstrap.sh") \
  -d "$DOMAIN" \
  -e "$EMAIL" \
  -r "$GITHUB_REPO"

cat <<INSTRUCTIONS

==========================================================
Bootstrap finished. NEXT (do these 4 steps inside this SSH session):
==========================================================

1. Generate a strong operator token + write all real keys to backend/.env:

   cd /home/ubuntu/already-here-command-os   # or /opt/command-os if you used the alt path
   OPERATOR_TOKEN=\$(openssl rand -hex 32)
   echo "Your OPERATOR_TOKEN: \$OPERATOR_TOKEN (save this in Bitwarden)"

   sudo nano backend/.env
   # Set/replace these lines:
   #   OPERATOR_TOKEN=<paste the value above>
   #   OPERATOR_EMAIL=$EMAIL
   #   LLM_API_KEY=<your Gemini / OpenAI / Anthropic key — type it here>
   #   STRIPE_API_KEY=<sk_test_... for now>
   #   AUTONOMY_LEVEL=L3
   #   DUAL_ACTOR_APPROVAL=true     # leave 'false' if single-operator
   # Save:  ctrl+O  enter  ctrl+X

2. Restart backend so the new env is picked up:

   sudo docker compose restart backend

3. Verify everything is live (returns JSON, not 502):

   curl -fsS https://$DOMAIN/api/governance/status
   curl -fsS https://$DOMAIN/api/system/status
   curl -fsS https://$DOMAIN/api/revenue-equation/equation

4. Open https://$DOMAIN in your browser and log in with OPERATOR_TOKEN.

If a curl returns 502, wait 60s for containers to settle then retry. If still
broken: sudo docker compose logs backend --tail 80
INSTRUCTIONS
