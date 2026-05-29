# Already Here Command OS — DEPLOY-NOW (Oracle Cloud Always Free)

> One job: get `https://alreadyherellc.com` (or your domain) serving the dashboard
> on **$0/month** infrastructure. Read top → bottom, do every step in order, do
> not skip. Total time: ~20 minutes if nothing goes wrong, ~45 if it does.

This guide is written for someone who has **never used Oracle Cloud before** and
gets stuck at the SSH step. If you've already done OCI + SSH before, jump to §3.

---

## Pre-flight (one-time, 2 minutes)

You need three things in front of you before you start:

1. **Domain name** that you own (alreadyherellc.com, or anything you own at GoDaddy/Namecheap/Cloudflare).
2. **GitHub repo URL** for this codebase (e.g. `https://github.com/<you>/already-here-command-os.git`).
   - If you haven't pushed yet: use the **"Save to GitHub"** button in this chat input. That's the fastest path.
3. **Oracle Cloud account**: free signup at <https://cloud.oracle.com/>. Credit-card required for ID check; you won't be charged. Pick **the home region nearest to you** — *never* change it later. Write it down.

---

## §1 — Create the OCI VM (PICK THESE EXACT VALUES — DO NOT IMPROVISE)

The user-reported pain has always been picking the wrong instance. Use **exactly these**:

1. From the OCI console: **Compute → Instances → Create Instance**.
2. **Name:** `command-os-prod` (no spaces, no caps).
3. **Image:** click *Change image* →
   - Source: `Oracle`
   - OS: **Canonical Ubuntu**
   - Version: **`22.04`**  ← NOT 20.04. NOT 24.04. Exactly `22.04`. Anything else and Docker repos fail or systemd-resolved fights you.
4. **Shape:** click *Change shape* →
   - Instance type: **Virtual machine**
   - Shape series: **Ampere**
   - Shape name: **`VM.Standard.A1.Flex`**
   - OCPUs: **2**, Memory: **12 GB**.
   - (This is *Always Free* — you get 4 OCPU/24 GB total ARM Ampere; using half. No credit card charge ever.)
5. **Networking:**
   - VCN: *Create new* — accept defaults.
   - Subnet: **Public Subnet** (critical — without this you cannot SSH in).
   - **Assign a public IPv4 address**: **YES**.
6. **Add SSH keys:**
   - Pick **"Generate a key pair for me"**.
   - Click **"Save Private Key"** — you will get a file like `ssh-key-2026-02-XX.key`. **PUT IT SOMEWHERE YOU CAN FIND IT.** Without this file you can never log in. Recommended path: `~/Downloads/oci-key.key` on your laptop.
   - Also click **"Save Public Key"** for later reference (optional).
7. **Boot volume:** leave defaults (47 GB).
8. Click **Create**. Wait ~90 seconds for status to become **RUNNING** (green).
9. Once running, on the instance details page, **copy the *Public IP address***. It looks like `129.213.XX.XX`. Write it down.

---

## §2 — Open the firewall (so port 80/443 are reachable)

OCI blocks all ports by default. Open 80 (HTTP) and 443 (HTTPS):

1. From the instance page, click the **VCN name** (link in the *Primary VNIC* section).
2. Click **Security Lists** → **Default Security List for vcn-XXX**.
3. Click **Add Ingress Rules**:
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** TCP
   - **Destination Port Range:** `80,443`
   - Description: `web`
4. Click **Add Ingress Rules** again.

---

## §3 — Point your domain at the server (2 minutes)

In your DNS provider (GoDaddy / Namecheap / Cloudflare), add **two A-records**:

| Type | Name | Value (your OCI public IP) | TTL |
|---|---|---|---|
| A | `@` | `129.213.XX.XX` | 600 |
| A | `www` | `129.213.XX.XX` | 600 |

DNS can take 5–30 minutes to propagate. Verify with:
```bash
# from your laptop terminal, replace alreadyherellc.com with your domain
dig +short alreadyherellc.com
# should return your OCI public IP
```

---

## §4 — SSH into the server (this is where you got stuck before)

Open the **Terminal** on your laptop (macOS: `cmd+space` → "Terminal"; Windows: WSL or PowerShell):

```bash
# 1. Move into the folder where your key file lives
cd ~/Downloads

# 2. Lock down permissions so SSH will actually accept the key
chmod 600 oci-key.key

# 3. Connect. Replace 129.213.XX.XX with YOUR OCI public IP.
ssh -i oci-key.key ubuntu@129.213.XX.XX
```

**If you see "Permission denied (publickey)":**
- Did you use the **private** key (the `.key` file), not the public key?
- Is the username **`ubuntu`** (NOT `root`, NOT `opc`, NOT your local username)?
- Did you `chmod 600`?
- Is the IP correct? Re-copy from the OCI console.

**If you see "Connection timed out":**
- You skipped §2 (firewall). Go back and add the ingress rules.

Once connected your prompt will look like:
```
ubuntu@command-os-prod:~$
```

---

## §5 — Run the one-command bootstrap

Still inside the SSH session, paste **this single line** (replace the three placeholders):

```bash
curl -fsSL https://raw.githubusercontent.com/<YOUR_GITHUB>/<YOUR_REPO>/main/scripts/oci-bootstrap.sh | sudo bash -s -- \
  -d alreadyherellc.com \
  -e you@your-real-email.com \
  -r https://github.com/<YOUR_GITHUB>/<YOUR_REPO>.git
```

What this does (you don't have to do any of it manually):
- Installs Docker + Docker Compose
- Auto-detects RAM (12 GB → MongoDB mode)
- Clones the repo
- Writes a Caddyfile that gets you **free HTTPS** via Let's Encrypt
- Starts the backend, frontend, MongoDB, and Caddy as background services
- Reverse-proxies your domain → the running stack

Watch the output. When you see:

```
[bootstrap] DEPLOY COMPLETE
[bootstrap] Visit: https://alreadyherellc.com
```

…you're done with the install. Open the domain in your browser.

---

## §6 — Required `.env` values (do this immediately after first boot)

The bootstrap creates `/home/ubuntu/already-here-command-os/backend/.env` with safe defaults. **Before you take any real money you must override:**

```bash
sudo nano /home/ubuntu/already-here-command-os/backend/.env
```

Set at minimum:
```
OPERATOR_TOKEN=<paste a long random string here, e.g. `openssl rand -hex 32`>
OPERATOR_EMAIL=you@your-real-email.com
LLM_API_KEY=<your Google AI Studio / Anthropic / OpenAI key>
STRIPE_API_KEY=<sk_test_... for now; sk_live_... when ready for real money>
AUTONOMY_LEVEL=L3       # L3 = bounded autonomy with HITL on critical gates
DUAL_ACTOR_APPROVAL=true  # require 2-of-2 sign-off on L5 gates
```

Save (`ctrl+O`, `enter`, `ctrl+X`), then restart:
```bash
cd /home/ubuntu/already-here-command-os
sudo docker compose restart backend
```

---

## §7 — Verify (60 seconds)

```bash
# governance status — confirm autonomy + dual-actor are wired
curl -fsS https://alreadyherellc.com/api/governance/status

# system status — confirm operator + llm + stripe are all configured
curl -fsS https://alreadyherellc.com/api/system/status

# revenue-equation — confirm Master Revenue Equation is live
curl -fsS https://alreadyherellc.com/api/revenue-equation/equation
```

If all three return JSON (not 502/timeout), you are live.

---

## §8 — Stripe go-live (when ready for real revenue)

Follow `/app/LIVE_MODE_CHECKLIST.md` step-by-step. Highlights:
1. Swap `STRIPE_API_KEY=sk_test_…` → `sk_live_…` in `backend/.env`.
2. Add `STRIPE_WEBHOOK_SECRET=whsec_…` (paste from the live webhook you create at <https://dashboard.stripe.com/webhooks>).
3. Restart backend.
4. Hit `POST /api/payments/smoke-test/create` — pays $0.50, immediately refunds.
5. When the smoke-test status shows `verified_live_pipeline: true`, you are clear to route real customers.

---

## Troubleshooting (the three things you'll actually hit)

**"Docker permission denied" inside SSH:**
```bash
sudo usermod -aG docker $USER && newgrp docker
```

**"Let's Encrypt failed: certificate request timed out"** → DNS hasn't propagated yet. Wait 10 min, run `sudo docker compose restart caddy`.

**"502 Bad Gateway" on the domain right after install** → backend is still booting. Wait 60s and refresh. If still 502 after 2 min:
```bash
cd /home/ubuntu/already-here-command-os
sudo docker compose logs backend --tail 100
```
Read the last 20 lines — almost always a missing env var.

---

## After you're live (Day 2)

- Set up nightly SQLite/Mongo backups: `sudo bash scripts/install-backup-cron.sh`
- Install the dashboard as a PWA on your phone (Safari/Chrome → Add to Home Screen).
- Mount a phone shortcut to `/overview`. Check the Master Revenue Equation card every morning — the **bottleneck variable** tells you exactly which lever to pull that day.
