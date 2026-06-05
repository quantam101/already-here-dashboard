# Final OCI Deploy — One Command

> **Tldr:** You (or any DevOps person) run a single command after creating the OCI instance. The bootstrap is self-healing, RAM-aware, and idempotent.

## 0. Prerequisites (5 minutes, all free)

- An Oracle Cloud Always Free tenancy (https://cloud.oracle.com → sign up)
- The `alreadyherellc.com` domain (GoDaddy, already owned)
- An SSH key pair on your laptop. If you don't have one:

  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/oci_cmdos -C "cmdos@$(hostname)"
  cat ~/.ssh/oci_cmdos.pub      # ← paste this into the OCI form below
  ```

## 1. Create the instance

OCI Console → **Compute → Instances → Create instance**:

| Field | Value |
|---|---|
| Name | `cmdos` |
| Image | **Canonical Ubuntu 22.04** (NOT 20.04 — it's EOL) |
| Shape | `VM.Standard.E2.1.Micro` (Always Free, AMD, 1 GB RAM) |
| Networking | Default VCN, **Assign public IPv4** |
| Add SSH keys | Paste the contents of `~/.ssh/oci_cmdos.pub` |
| Advanced → Management → User data | Paste the **two-line script** below |

**User data (two lines, paste exactly):**

```bash
#!/bin/bash
curl -fsSL https://raw.githubusercontent.com/Quantam101/already-here-dashboard/main/cloud-init.sh | bash
```

Click **Create**. Note the **public IP** that appears (e.g., `144.24.60.159`).

## 2. Point DNS at the IP

GoDaddy → DNS Management for `alreadyherellc.com`:

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `@` | `<your-instance-ip>` | 600 |
| A | `www` | `<your-instance-ip>` | 600 |

## 3. Watch the bootstrap (~10 minutes)

```bash
ssh -i ~/.ssh/oci_cmdos ubuntu@<your-instance-ip>
sudo tail -f /var/log/command-os-bootstrap.log
```

Wait for `BOOTSTRAP COMPLETE`. The bootstrap is **fully idempotent** — if SSH disconnects, re-connect and run:

```bash
sudo bash /opt/command-os/scripts/oci-bootstrap.sh -d alreadyherellc.com -e dispatch@alreadyherellc.com -r https://github.com/Quantam101/already-here-dashboard.git
```

## 4. Drop in your secrets

```bash
sudo nano /opt/command-os/backend/.env
```

Fill in the three fields:

```env
[removed]"sk-[removed]"           # from [removed] → Profile → Universal Key
STRIPE_API_KEY="sk_test_[removed]"            # keep test for now; flip to sk_live_... later
OPERATOR_EMAIL="alreadyherellc@gmail.com"    # locks dashboard to this Google account
```

Save → Ctrl+O → Enter → Ctrl+X.

```bash
cd /opt/command-os
sudo docker compose -f docker-compose.sqlite.yml restart backend
```

## 5. Verify live

```bash
# From your laptop:
curl -fsS https://alreadyherellc.com/api/health/
curl -fsS https://alreadyherellc.com/api/system/status | python3 -m json.tool
```

Open https://alreadyherellc.com → Google login → dashboard renders → Quickstart Wizard opens.

## 6. Switch Stripe to live (when ready)

Follow **`LIVE_MODE_CHECKLIST.md`** in this repo. The backend has a safety gate: a live key without a webhook secret will be **refused** at checkout creation — no silent failures.

---

## What's running

```
/opt/command-os/
├── backend/.env                        # secrets (you edit this)
├── docker-compose.sqlite.yml           # the active compose file (2 containers)
├── frontend/build/                     # pre-built React bundle (built on host at bootstrap)
├── Caddyfile.sqlite                    # auto-HTTPS reverse proxy
└── data/command_os.db                  # SQLite database (persisted on host disk)

Containers:
  backend  - FastAPI + uvicorn on :8001 (400 MB limit)
  caddy    - Reverse proxy + auto-Let's Encrypt cert (100 MB limit)
```

Memory budget: backend ~200 MB + Caddy ~30 MB ≈ **230 MB** out of 1 GB available.

## Daily ops

```bash
# Logs:
sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml logs -f

# Restart everything:
sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml restart

# Backup the SQLite DB:
sudo bash /opt/command-os/scripts/backup-sqlite.sh

# Install automated nightly backups (one-time, ~30 sec):
sudo bash /opt/command-os/scripts/install-backup-cron.sh

# Update to latest code from GitHub:
cd /opt/command-os
sudo git pull
sudo docker compose -f docker-compose.sqlite.yml up -d --build
```

## If the bootstrap hangs or fails

1. **Don't panic.** SSH back in: `ssh -i ~/.ssh/oci_cmdos ubuntu@<ip>`
2. Check the log: `sudo tail -n 100 /var/log/command-os-bootstrap.log`
3. Resume manually:

   ```bash
   sudo bash /opt/command-os/scripts/oci-bootstrap.sh \
     -d alreadyherellc.com \
     -e dispatch@alreadyherellc.com \
     -r https://github.com/Quantam101/already-here-dashboard.git
   ```

4. If it still fails, paste the last 30 lines of `/var/log/command-os-bootstrap.log` to the agent or to your DevOps freelancer — the bootstrap is plain bash and the error message tells you exactly where it died.

---

**Total cost from this guide onward: $0/month forever**, assuming you stay on the OCI Always Free tier (`VM.Standard.E2.1.Micro`).
