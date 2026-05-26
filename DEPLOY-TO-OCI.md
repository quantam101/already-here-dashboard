# Deploy Already Here Command OS to Oracle Cloud Always Free
## Production setup for `alreadyherellc.com` — $0/month forever

This guide walks you through provisioning a free OCI compute instance, pointing your GoDaddy domain at it, and bringing the dashboard live.

**Time:** ~30 minutes. **Cost:** $0/month forever (OCI Always Free + Let's Encrypt + free Docker).

---

## Step 1 — Provision the free OCI instance (5 min)

1. Sign in to https://cloud.oracle.com (create an account if you don't have one — free tier signup requires a credit card for verification but **is never charged** if you stay on Always Free shapes).
2. Click **Compute → Instances → Create Instance**.
3. Image: **Ubuntu 22.04** (or 24.04). Shape: **VM.Standard.A1.Flex** (4 OCPU / 24 GB RAM ARM — always free) OR **VM.Standard.E2.1.Micro** (always free x86, smaller).
4. Networking: keep defaults; **assign a public IPv4 address**.
5. **Generate SSH keys** in the console, download both the private + public key. Save the private key as `~/.ssh/oci_command_os` on your laptop.
6. Click **Create**. Note the **Public IP Address** that appears (call it `<OCI_IP>`).

## Step 2 — Open ports 80 + 443 in OCI VCN (2 min)

OCI defaults to blocking inbound traffic at two layers — both need to be opened:

1. **Security List**: Networking → Virtual Cloud Networks → click your VCN → Security Lists → Default → **Add Ingress Rules** twice:
   - Source CIDR `0.0.0.0/0`, IP Protocol `TCP`, Destination Port `80`
   - Source CIDR `0.0.0.0/0`, IP Protocol `TCP`, Destination Port `443`
2. The bootstrap script will also enable `ufw` on the instance itself.

## Step 3 — Point GoDaddy DNS at OCI (5 min — propagation takes 1-24h)

1. Log into https://account.godaddy.com → My Products → DNS for `alreadyherellc.com`.
2. **Delete** any existing default A-record for `@` (the parking page).
3. **Add these records:**

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `@` | `<OCI_IP>` (from Step 1) | 600 |
| A | `www` | `<OCI_IP>` | 600 |

4. Save. Open https://dnschecker.org/#A/alreadyherellc.com — wait until your `<OCI_IP>` shows up green globally (usually 5-30 min for GoDaddy).

## Step 4 — SSH in and run the one-command bootstrap (5 min)

```bash
ssh -i ~/.ssh/oci_command_os ubuntu@<OCI_IP>
```

Once in:

```bash
# 1. Export your env BEFORE running the bootstrap (keys stay on the server)
export EMERGENT_LLM_KEY="sk-emergent-..."      # ask Emergent Profile → Universal Key
export STRIPE_API_KEY="sk_live_..."             # from dashboard.stripe.com/apikeys
export OPERATOR_EMAIL="your@email.com"          # ONLY this email can log in

# 2. Download + run the bootstrap (replace <YOUR_GH_REPO> with your repo URL)
curl -fsSL https://raw.githubusercontent.com/<YOUR_GH_REPO>/main/scripts/oci-bootstrap.sh -o /tmp/bootstrap.sh
sudo -E bash /tmp/bootstrap.sh \
  -d alreadyherellc.com \
  -e your@email.com \
  -r https://github.com/<YOUR_GH_REPO>.git
```

What this does:
- Installs Docker + Compose v2
- Opens host firewall for tcp/80,443
- Clones your repo to `/opt/command-os`
- Generates `/opt/command-os/backend/.env` and `frontend/.env` from your exported env vars
- Generates `Caddyfile` with `alreadyherellc.com` + auto-HTTPS via Let's Encrypt
- Runs `docker compose up -d --build` — pulls Mongo, builds backend + frontend, brings everything up

**Watch logs:** `docker compose -f /opt/command-os/docker-compose.yml logs -f`

## Step 5 — Verify live (2 min)

After ~3 min for Caddy to obtain certificates:

```bash
curl -fsSL https://alreadyherellc.com/api/health
# → {"status":"healthy","timestamp":"2026-..."}
```

Open https://alreadyherellc.com in your browser. You'll be redirected to Google login (because `OPERATOR_EMAIL` is set). Sign in with that email → land in Command Center.

## Step 6 — Stripe webhook (3 min)

1. Go to https://dashboard.stripe.com/webhooks → **Add endpoint**
2. URL: `https://alreadyherellc.com/api/payments/webhook`
3. Events: `checkout.session.completed`, `checkout.session.expired`
4. Save → copy the **Signing secret** → add to `/opt/command-os/backend/.env`:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```
5. `cd /opt/command-os && docker compose restart backend`

## Step 7 — PWA install on phone (1 min)

Open https://alreadyherellc.com on:
- **iPhone Safari** → tap *Share* → *Add to Home Screen*
- **Android Chrome** → tap *⋮* → *Install app*

The dashboard now lives on your home screen as a real app icon, green theme, "Command OS" name.

---

## You're live

- Dashboard: https://alreadyherellc.com
- Health: https://alreadyherellc.com/api/health
- Pricing/sell page: https://alreadyherellc.com/pricing
- Stripe accepts real money: ✅
- Auto-cycle runs at 07:00 UTC daily: ✅
- $25K Proof-of-Work meter ticks on every paid sale: ✅

## Daily ops

| Action | Where |
|---|---|
| Generate today's content drafts | `Run Cycle` button on Command Center |
| Review what to do next | `/analytics` → AI Operations Advisor |
| Publish content manually | export from `/studio` → post → `Log Post` |
| Record earnings | `/proof-of-work` → `Record Earnings` |
| Generate a book to sell | `/books` → `Generate Book` → download .md → upload to KDP |
| Share pricing link | `/pricing` → `Generate Share Link` (UTM-tagged) |

## Recovering from OCI restart

`docker compose` is set to `restart: unless-stopped` — the stack auto-recovers on reboot. Database is persisted to the `mongo-data` Docker volume. Snapshots: run `/opt/command-os/scripts/backup.sh` weekly (cron suggestion: `0 3 * * 0 /opt/command-os/scripts/backup.sh`).

## Switching back to test Stripe / disabling auth

Edit `/opt/command-os/backend/.env`:
- `STRIPE_API_KEY=sk_test_emergent` (test mode)
- comment out / blank `OPERATOR_EMAIL=` (auth falls open)

Then `docker compose restart backend`.
