#!/usr/bin/env bash
# One-shot HF Space deploy for D-ASI Kernel.
#
# Usage:
#   export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#   export HF_USER=AlreadyHereLLC          # your HF username
#   export HF_SPACE_NAME=dasi-kernel       # your target Space name
#   bash /app/dasi/deploy_to_hf.sh
#
# What it does:
#   1. Creates (or re-uses) a Docker-SDK HF Space at $HF_USER/$HF_SPACE_NAME
#   2. Clones it via Git over HTTPS using $HF_TOKEN
#   3. Copies the 4 production files + README into the working tree
#   4. Sets the HF_TOKEN repo-secret on the Space (so the kernel can call Inference)
#   5. Commits + pushes — the Space auto-builds and exposes :7860

set -euo pipefail

: "${HF_TOKEN:?HF_TOKEN is required}"
: "${HF_USER:?HF_USER is required}"
: "${HF_SPACE_NAME:?HF_SPACE_NAME is required}"

SRC_DIR="$(dirname "$(readlink -f "$0")")"
WORK_DIR="$(mktemp -d -t dasi-deploy.XXXXXX)"
SPACE_REPO="$HF_USER/$HF_SPACE_NAME"
SPACE_URL="https://huggingface.co/spaces/$SPACE_REPO"

echo "[1/5] Ensuring Python huggingface_hub is available..."
python3 -m pip install --quiet --upgrade "huggingface_hub>=1.5.0"

echo "[2/5] Creating (or re-using) Docker Space '$SPACE_REPO'..."
python3 - <<PY
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])
api.create_repo(
    repo_id=os.environ["HF_USER"] + "/" + os.environ["HF_SPACE_NAME"],
    repo_type="space",
    space_sdk="docker",
    exist_ok=True,
)
print(f"  Space ready: {os.environ['HF_USER']}/{os.environ['HF_SPACE_NAME']}")
PY

echo "[3/5] Cloning Space repo into $WORK_DIR..."
git clone --quiet "https://${HF_USER}:${HF_TOKEN}@huggingface.co/spaces/${SPACE_REPO}" "$WORK_DIR"

echo "[4/5] Copying production assets..."
cp -f "$SRC_DIR/Dockerfile"           "$WORK_DIR/Dockerfile"
cp -f "$SRC_DIR/requirements.txt"     "$WORK_DIR/requirements.txt"
cp -f "$SRC_DIR/agent_manifest.yaml"  "$WORK_DIR/agent_manifest.yaml"
cp -f "$SRC_DIR/main.py"              "$WORK_DIR/main.py"
cp -f "$SRC_DIR/README.md"            "$WORK_DIR/README.md"

echo "[5/5] Setting HF_TOKEN repo secret on the Space..."
python3 - <<PY
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])
api.add_space_secret(
    repo_id=os.environ["HF_USER"] + "/" + os.environ["HF_SPACE_NAME"],
    key="HF_TOKEN",
    value=os.environ["HF_TOKEN"],
)
print("  HF_TOKEN secret set on the Space.")
PY

cd "$WORK_DIR"
git -c user.email="ops@alreadyhere.llc" -c user.name="D-ASI Deployer" add .
if git -c user.email="ops@alreadyhere.llc" -c user.name="D-ASI Deployer" diff --staged --quiet; then
    echo "  No file changes — Space already up to date."
else
    git -c user.email="ops@alreadyhere.llc" -c user.name="D-ASI Deployer" \
        commit -q -m "D-ASI v4.0.0-ENTERPRISE — automated deploy"
    git push -q origin main || git push -q origin master
    echo "  Push complete."
fi

echo ""
echo "✓ Deployed. Build status + URL:"
echo "  $SPACE_URL"
echo ""
echo "Once the Space build turns green (~2-3 min), smoke-test:"
echo ""
echo "  SPACE='https://$(echo "$HF_USER" | tr '[:upper:]' '[:lower:]')-$(echo "$HF_SPACE_NAME" | tr '[:upper:]' '[:lower:]').hf.space'"
echo "  curl \"\$SPACE/health\""
echo "  curl -X POST \"\$SPACE/matrix/execute\" -H 'Content-Type: application/json' \\"
echo "       -d '{\"directive\":\"Output JSON list of 3 zero-trust routing rules. Pure JSON only.\"}'"
echo "  curl \"\$SPACE/matrix/telemetry\""

rm -rf "$WORK_DIR"
