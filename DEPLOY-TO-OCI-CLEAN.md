# OCI Clean Deploy — paste-resistant, $0/month

This recipe eliminates the paste-mangling problem completely. You only paste **two short lines** into OCI's cloud-init box. The actual bootstrap is fetched from GitHub at boot time.

**Total cost: $0/month forever.** No fighting OCI tooling — your SSH key is set up at instance creation, so you can fix anything afterward.

---

## What you'll do

| # | Step | Time |
|---|---|---|
| 1 | Terminate the broken instance + clean up DNS | 2 min |
| 2 | Create a new instance with proper SSH key + 2-line cloud-init | 3 min |
| 3 | Wait for boot + auto-deploy | 10 min |
| 4 | SSH in + add your secrets via env file | 2 min |
| 5 | Update DNS + verify | 5 min |
| **Total** | **22 minutes** | |

---

## Step 1 — Terminate `os-dashboardAlways Free` + clean up

1. **OCI Console** → Compute → Instances → click **`os-dashboardAlways Free`**
2. Top → **More Actions → Terminate**
3. ✅ Check "Permanently delete the attached boot volume"
4. Click **Terminate instance** → wait until state = **Terminated**

---

## Step 2 — Create the new instance

1. **Compute → Instances → Create instance**
2. **Name:** `cmdos`
3. **Image:** Change Image → **Canonical Ubuntu** → **22.04** → Select
4. **Shape:** keep `VM.Standard.E2.1.Micro` (Always Free)
5. **Primary VNIC:** keep existing VCN/subnet · ✅ Assign public IPv4

### SSH key — paste YOUR public key
6. SSH keys section → select **"Paste public keys"**
7. Paste exactly this one line (it's the one you generated in Cloud Shell earlier — I have it from chat history):

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCc9bbH4rWxMbENW5DOBRm4+pw0Cb49mxU1eTbYt+HpEWIW7MM7dqtoIZE3zlaFvsbcJdbwB2togRYabMAU1r+UKp8IJ8OkE/4JD1ThR/W2b8Q81wAeHrNeSJLL0GlIZZD7q92XiZls7rfju/hDuWlJOHZWY1Zdk+dIZ6hmM6IHtWhiZqtSPXs7kanXTmJxbbnW4KVT7Oa6oKHDrwNSgiMsf7Yy2axn5QWUBqvWlASgP9BfNmt3qB+8ZZOL6aCOb2w/8SH/oqPh4hdMzKaDYd9llLsWCcc3gpfXslMX/+Ac0cMkTxTpfci1aw5Ls9as9SRuD1BrDQLBoJOuY6vYZrLlJQ3Ln4LEy+mbo+df3vF7NxLuyXrScnDywYH5zfmXPrsQqADZyGfuzVDOgEEC0JOHnia0lPmeXJftK37iMAvofWUMc4TGolW3Hpbv+aLUJXt+DUCl9ykKMX7s+SK49lBjgH1QWk2ILVrE8LIrh12RsNHrDSOGeBbMCA4TEnBG+Gx+bM7NqiGV9uwcoW+QWB/Wh5Az/FPQElgSKTKUOb1ZyNPvVMXWyxY4UmjdXoZbLLV+iUnK74ZsK+U5p0OsckS4975qLv2/YRLjd9Tv4XjrpFhDxY8FmG52WYprUhD313WLnSeWvrfYlJI8tU9DehkkkHbwnG69QCswB0GNaKVxqw== cmdos@cloudshell
```

### Cloud-init — paste only TWO lines
8. **Click "Show advanced options"** ← critical, easy to miss
9. Scroll to **Management** → **Initialization script** → select **"Paste cloud-init script"**
10. In the textarea, paste **exactly these two lines** (no edits needed — no secrets, no custom values):

```
#!/bin/bash
curl -fsSL https://raw.githubusercontent.com/Quantam101/already-here-dashboard/main/cloud-init.sh | bash
```

That's it. Two lines. Nothing to mangle.

11. Click **Create** at the bottom

---

## Step 3 — Wait for boot + auto-deploy

After ~30 seconds, instance state = **Running**. **Note the new public IP** (will be different from old).

The cloud-init runs in the background for ~10 minutes:
- Installs Docker + Node
- Builds the React static bundle
- Starts the stack with `docker compose -f docker-compose.sqlite.yml up -d`

You can verify it's progressing by pinging port 22:

```bash
# In OCI Cloud Shell:
nc -z <NEW_IP> 22 && echo "SSH up"
nc -z <NEW_IP> 80 && echo "Caddy up"
```

Port 80 opens when bootstrap finishes (~10 min).

---

## Step 4 — SSH in + add secrets

Once port 22 is open (immediately after boot, even before bootstrap finishes), you can SSH in to monitor:

In **OCI Cloud Shell** (your existing one — already has `~/.ssh/cmdos`):

```bash
ssh -i ~/.ssh/cmdos -o StrictHostKeyChecking=no ubuntu@<NEW_IP>
```

Your prompt becomes `ubuntu@cmdos:~$`. You're in.

**Watch the deploy live:**

```bash
sudo tail -f /var/log/command-os-bootstrap.log
```

When you see `BOOTSTRAP COMPLETE: ...`, press **Ctrl+C** to exit.

**Now add your secrets:**

```bash
sudo nano /opt/command-os/backend/.env
```

Edit these three lines (use arrow keys to navigate, type to edit):

```
EMERGENT_LLM_KEY="sk-emergent-PASTE_YOUR_FRESH_KEY"
STRIPE_API_KEY="sk_test_emergent"
OPERATOR_EMAIL="your@email.com"
```

Save: **Ctrl+O**, Enter, **Ctrl+X**.

**Restart the backend to pick up the new env:**

```bash
cd /opt/command-os
sudo docker compose -f docker-compose.sqlite.yml restart backend
```

Verify:

```bash
curl -s http://localhost:8001/api/health/
curl -s http://localhost:8001/api/system/status | head -c 500
```

---

## Step 5 — Update DNS + verify HTTPS

1. **GoDaddy DNS** for `alreadyherellc.com`:
   - Edit the `@` A-record → change Value to the new IP from Step 3
   - Save (TTL 600 is fine)
2. Wait 5-15 min for propagation
3. Caddy auto-fetches Let's Encrypt cert once DNS resolves

**Verify from anywhere:**
- https://alreadyherellc.com/api/health/ → `{"status":"healthy",...}`
- https://alreadyherellc.com → Google login → Quickstart Wizard

---

## Why this version works when others didn't

1. **Two-line cloud-init paste** = no special chars to mangle
2. **The actual logic lives on GitHub** = no version drift between what you pasted and what runs
3. **YOUR real SSH key set at creation** = you have access immediately, can fix anything from SSH
4. **No secrets in cloud-init** = you add them after deploy, when you have a working shell
5. **No reliance on broken OCI agent** for Run Command — pure cloud-init at boot time

---

## If something still breaks

- **Port 22 doesn't open within 5 min** → Instance bootstrap died early. View boot log via OCI's serial console (use a public-key auth instead of password)
- **Port 80 doesn't open within 15 min** → SSH in and `sudo tail -100 /var/log/command-os-bootstrap.log` — paste the last 30 lines back to me
- **HTTPS cert won't issue** → DNS not propagated yet. Wait. Or `sudo docker compose -f docker-compose.sqlite.yml logs caddy --tail 30`
- **Frontend loads but says "loading"** forever → `REACT_APP_BACKEND_URL` mismatch. SSH in and check `/opt/command-os/frontend/.env`
