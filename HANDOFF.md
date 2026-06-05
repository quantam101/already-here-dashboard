# Already Here Command OS — Deploy Handoff (for any DevOps freelancer)

> **Target turnaround:** 60–90 minutes  
> **Budget:** $50–150 flat fee is reasonable. This is a routine OCI deployment.  
> **Operator contact:** alreadyherellc@gmail.com

---

## TL;DR for the freelancer

You're deploying a **production-ready FastAPI + React app** to **Oracle Cloud Always Free**. The code, tests, Docker config, Caddy config, and bootstrap scripts are all done. The operator has hit terminal/SSH access issues that they cannot resolve via OCI Cloud Shell. **They need someone with their own SSH-capable terminal to take this across the finish line.**

You will:
1. Get OCI tenancy access OR a public IP + private SSH key from the operator
2. SSH in (or recreate the instance with your own SSH key)
3. Run the bootstrap (one curl command)
4. Wait 10 minutes
5. Verify the site is live at `https://alreadyherellc.com`

That's the entire scope.

---

## What you're deploying

A FastAPI + React application:

- **Code:** https://github.com/Quantam101/already-here-dashboard (public, includes all deploy artifacts)
- **Target server:** Oracle Cloud Always Free, Ubuntu, public IP **144.24.60.159**  (region: us-phoenix-1)
- **Target domain:** **alreadyherellc.com** (GoDaddy DNS A-record currently points at the IP above)
- **HTTPS:** Caddy + Let's Encrypt (auto-issued)
- **Database:** SQLite on persistent disk (host is 1 GB RAM, MongoDB is too heavy)
- **Required end state:** `https://alreadyherellc.com` returns the dashboard with HTTPS, Google login works, Quickstart Wizard appears.

## Current blocker (why operator handed off)

- Operator tried multiple times via OCI Cloud Shell. Hit:
  - Cloud-init paste mangling (long SSH key got truncated in OCI form)
  - Docker install failure (`get.docker.com` tries to install `docker-model-plugin` which doesn't exist on Ubuntu 20.04 focal — EOL)
  - OCI Cloud Shell intermittently times out connecting to the instance even when port 22 is open from the public internet
- **All of the above are operator-environment issues, not code issues.** The repo is healthy: 104/104 backend tests passing, deploy scripts patched, all artifacts committed.

## Status when handed off

- ✅ GitHub repo public + complete
- ✅ Cloud-init script committed at `/cloud-init.sh` on main branch
- ✅ Bootstrap script at `/scripts/oci-bootstrap.sh` — RAM auto-detect, picks SQLite mode for `<1500MB`
- ✅ Docker install hand-rolled to handle Ubuntu 20.04 Focal EOL (skips `docker-model-plugin` which doesn't exist on focal)
- ✅ SSH key for `ubuntu@` is hardcoded into `cloud-init.sh` (operator's public key — installs automatically at boot)
- ❌ Bootstrap has failed multiple times on previous OCI instance. **Recommend nuking the existing instance and starting clean** — see Step 1.

## SSH access for you

Two options:

1. **Operator's existing key** — already embedded in `cloud-init.sh` (works only from operator's machine). Easier: just create a new instance with your own SSH key pasted in the OCI form, and the instance will accept your key too.
2. Ask operator for the OCI tenancy console login. They'll be at `alreadyherellc@gmail.com` / tenancy `alreadyherellc`, region `us-phoenix-1`.

---

## Deploy procedure (definitive)

### Step 1 — Nuke the broken instance

In OCI Console:
- Compute → Instances → terminate `cmdos` (or whatever is at `144.24.60.159`) with "Permanently delete attached boot volume"

### Step 2 — Create a fresh instance

- Name: `cmdos`
- Image: **Canonical Ubuntu 22.04** (NOT 20.04 — the bootstrap also handles 22, but 22 is cleaner)
- Shape: `VM.Standard.E2.1.Micro` (Always Free)
- Networking: assign public IPv4 in the existing VCN (security list already has 22, 80, 443 open)
- SSH keys: paste **your own public key**
- **Show advanced options → Management → Initialization script → Paste cloud-init script:**

```bash
#!/bin/bash
curl -fsSL https://raw.githubusercontent.com/Quantam101/already-here-dashboard/main/cloud-init.sh | bash
```

(Two lines, that's it. The fetched script handles everything.)

- Create instance. Note the new public IP.

### Step 3 — Update DNS (if IP changed)

- GoDaddy DNS for `alreadyherellc.com` → A record `@` → set value to new IP, TTL 600.

### Step 4 — Wait + watch

SSH in once port 22 opens (~60 sec post-create):

```bash
ssh -i ~/.ssh/your_key ubuntu@<NEW_IP>
sudo tail -f /var/log/command-os-bootstrap.log
```

The bootstrap runs ~10 minutes. Watch for `BOOTSTRAP COMPLETE`.

### Step 5 — Add secrets

```bash
sudo nano /opt/command-os/backend/.env
```

Fill in the three blanks (operator will provide values):
- `[removed]"sk-[removed]"` — from operator ([removed] Universal Key)
- `STRIPE_API_KEY="sk_test_[removed]"` — keep this for now (test mode)
- `OPERATOR_EMAIL="alreadyherellc@gmail.com"` — or whatever Google email operator wants

Save (Ctrl+O, Enter, Ctrl+X). Restart:

```bash
cd /opt/command-os
sudo docker compose -f docker-compose.sqlite.yml restart backend
```

### Step 6 — Verify

From your laptop:

```bash
curl -fsS https://alreadyherellc.com/api/health/
# → {"status":"healthy",...}
```

Browser: `https://alreadyherellc.com` → Google login → sign in as the OPERATOR_EMAIL → dashboard loads.

---

## Known landmines

- **Ubuntu 20.04 focal is EOL.** The official `get.docker.com` script tries to install `docker-model-plugin` which doesn't exist on focal. The bootstrap was patched to install Docker manually (`docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin` only). If you use a different image, this might not be needed.
- **A1.Flex (ARM) shapes are constantly out of capacity.** Stick with `VM.Standard.E2.1.Micro` (AMD).
- **OCI's "Run Command" and serial console are unreliable.** Don't depend on them — use SSH.
- **OCI textbox sometimes mangles long single-line SSH keys.** That's why the operator's key is hardcoded inside `cloud-init.sh`.

## Files you'll touch

```
/opt/command-os/
├── backend/.env              # secrets go here
├── docker-compose.sqlite.yml # the active compose file
├── Caddyfile.sqlite          # mounted into Caddy container
└── frontend/build/           # pre-built React static bundle (built at bootstrap time)
```

## Files you'll never touch

- The Mongo `docker-compose.yml` — not used on this host
- Anything under `/opt/command-os/.git`

## After-deploy checklist

- [ ] `https://alreadyherellc.com/api/health/` returns JSON `{"status":"healthy"}`
- [ ] `https://alreadyherellc.com/api/system/status` returns JSON with `stripe_mode`, `is_seeded`, etc.
- [ ] `https://alreadyherellc.com` loads in browser, shows login screen
- [ ] Google login with `OPERATOR_EMAIL` works → dashboard renders
- [ ] Quickstart Wizard auto-opens
- [ ] `docker compose -f docker-compose.sqlite.yml ps` shows 2 containers Up
- [ ] Memory usage `free -h` shows backend + caddy total under 500 MB

## If a step breaks

| Symptom | Fix |
|---|---|
| Cloud-init never runs | Check `sudo cat /var/log/cloud-init-output.log` — usually a typo in user-data |
| Port 22 never opens | Instance OS install failed. Recreate. |
| Port 80/443 never open | `sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml logs caddy backend --tail 50` |
| HTTPS cert won't issue | DNS not propagated — `dig +short alreadyherellc.com @1.1.1.1` should return the OCI IP |
| Google login rejects user | `OPERATOR_EMAIL` mismatch — fix in `.env` and restart backend |

## Operator handoff items needed from operator

1. Their **fresh** [removed] LLM key (operator may need to rotate first — instructions: https://app.[removed] → Profile → Universal Key)
2. The Google email they want to log in with (for `OPERATOR_EMAIL`)
3. Stripe API key — `sk_test_[removed] is fine for go-live, swap to `sk_live_...` later
4. (Optional) Stripe webhook signing secret if switching to live mode

## Contact

- **Operator email:** alreadyherellc@gmail.com
- **Repo issues:** https://github.com/Quantam101/already-here-dashboard/issues
- **Tenancy:** alreadyherellc (OCI region us-phoenix-1)
