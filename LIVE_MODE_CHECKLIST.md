# Stripe Live-Mode Go-Live Checklist

You are switching from `sk_test_emergent` (the placeholder) to your real Stripe keys to start collecting real money. This is the **exact** order to do it in. Stop on any failure.

> **Backend safety gate:** If you set a `sk_live_...` key but **forget to set** `STRIPE_WEBHOOK_SECRET`, the backend will **refuse** to create any new checkout (returns HTTP 503). This prevents silent revenue loss while you're still mid-setup. The gate is in `routes/payments.py::create_checkout`.

---

## 0. Pre-flight (do these in this order)

```bash
# from anywhere
curl -fsS https://alreadyherellc.com/api/payments/readiness | python3 -m json.tool
```

You'll see your current mode, the issues list, and the full checklist. Use this as your live source-of-truth — re-run after every step.

---

## 1. Pull live API key from Stripe

- https://dashboard.stripe.com → **Developers → API keys**
- Reveal **Secret key** (`sk_live_...`) — copy it
- Save it in your password manager **before pasting anywhere**

## 2. Add the live key to your deployed `.env`

SSH into the OCI box:

```bash
ssh -i ~/.ssh/your_key ubuntu@<your-instance-ip>
sudo nano /opt/command-os/backend/.env
```

Replace:

```env
STRIPE_API_KEY="sk_test_emergent"
```

with:

```env
STRIPE_API_KEY="sk_live_REPLACE_ME"
```

**Do not restart yet.** The webhook secret is required first.

## 3. Create the webhook in Stripe

- https://dashboard.stripe.com → **Developers → Webhooks → Add endpoint**
- Endpoint URL: `https://alreadyherellc.com/api/payments/webhook`
- Events to send: `checkout.session.completed` (and optionally `payment_intent.succeeded`)
- Click **Add endpoint**
- Click into the new endpoint → **Reveal Signing secret** → copy `whsec_...`

## 4. Add the webhook signing secret

```bash
sudo nano /opt/command-os/backend/.env
```

Add (or update):

```env
STRIPE_WEBHOOK_SECRET="whsec_REPLACE_ME"
OPERATOR_EMAIL="you@alreadyherellc.com"
```

Save (Ctrl+O, Enter, Ctrl+X).

## 5. Restart backend

```bash
cd /opt/command-os
sudo docker compose -f docker-compose.sqlite.yml restart backend
```

## 6. Verify

```bash
curl -fsS https://alreadyherellc.com/api/payments/readiness | python3 -m json.tool
```

Expected:

```json
{
  "stripe_mode": "live",
  "webhook_secret_set": true,
  "operator_email_set": true,
  "go_live_ready": true,
  "issues": []
}
```

If `go_live_ready` is `false`, the `issues` array tells you exactly what's missing.

## 7. End-to-end smoke test

- Browser: `https://alreadyherellc.com/pricing`
- Click **Starter — $49**
- Use a **real card** (your own) — Stripe will charge $49 → it lands in your Stripe balance, plus you can immediately refund yourself via the Stripe dashboard
- After redirect, you'll land on `/payment-success` → status should poll to `paid`
- Check `/proof-of-work` → ledger entry should appear under `rev-saas` for $49 (net ≈ $47.58 after Stripe fees)

## 8. (Optional) Set up Stripe Tax / VAT

- Stripe dashboard → **Tax → Settings** → enable for jurisdictions you sell into
- This is automatic — no code change required

---

## Rollback

If anything misbehaves, instantly revert to test mode:

```bash
sudo sed -i 's|^STRIPE_API_KEY=.*|STRIPE_API_KEY="sk_test_emergent"|' /opt/command-os/backend/.env
sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml restart backend
```

Live charges already collected are unaffected — they remain in your Stripe balance.

---

## Common mistakes

| Symptom | Cause | Fix |
|---|---|---|
| Checkout returns 503 "STRIPE_WEBHOOK_SECRET is missing" | You set live key but skipped step 3-4 | Complete steps 3 and 4 in order |
| Webhook events 400 in Stripe dashboard | Wrong signing secret | Re-copy from Stripe → Webhooks → endpoint → Signing secret |
| Payment succeeds but ledger entry missing | Webhook URL unreachable | `curl -X POST https://alreadyherellc.com/api/payments/webhook` should return 400 (signature missing), not connection-refused |
| Live mode but `/readiness` still says test | You forgot to restart the backend container | `docker compose -f docker-compose.sqlite.yml restart backend` |

---

## Where this is enforced in code

- **Mode detection:** `backend/routes/payments.py::_stripe_mode()` (sk_live → live, sk_test/sk_test_emergent → test)
- **Safety gate:** `backend/routes/payments.py::create_checkout()` — raises 503 if live without webhook secret
- **Webhook handler:** `backend/routes/payments.py::stripe_webhook()` — verifies signature via emergentintegrations SDK
- **Readiness probe:** `GET /api/payments/readiness` — returns checklist + gating issues
