# Stripe Live-Mode Go-Live Checklist

You are switching from `sk_test_[removed] (the placeholder) to your real Stripe keys to start collecting real money. This is the **exact** order to do it in. Stop on any failure.

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
STRIPE_API_KEY="sk_test_[removed]"
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

## 7. End-to-end smoke test — **auto-refunding $0.50 test charge**

The Command OS has a built-in live-mode smoke runner that creates a $0.50 live charge and **auto-refunds it within seconds** via the webhook. This lets you verify live keys + webhook signature + ledger plumbing **end-to-end** without losing money.

```bash
# 1. Create the smoke session
curl -fsS -X POST https://alreadyherellc.com/api/payments/smoke-test/create | python3 -m json.tool
```

Response includes a `url`. Open it in a browser, pay $0.50 with a real card (yours).

```bash
# 2. Poll the status — flips from "initiated" → "paid" → refunded within ~10 sec
SID="<the session_id from step 1>"
curl -fsS https://alreadyherellc.com/api/payments/smoke-test/status/$SID | python3 -m json.tool
```

Look for:

```json
{
  "payment_status": "refunded",
  "smoke_refund_status": "succeeded",
  "verified_live_pipeline": true
}
```

If `verified_live_pipeline: true` → **your live Stripe integration is wired correctly.**

If `smoke_refund_status` is `"error: ..."` → the webhook fired but the refund call failed (usually wrong API key or the charge hasn't settled yet — wait 30s and re-poll).

Smoke-test charges:
- Never write to the ledger (the webhook short-circuits before `_record_paid_to_ledger`)
- Are tagged `package_id=smoke_test` in `payment_transactions` so they're trivially distinguishable from real revenue.
- List the last 10 via: `GET /api/payments/smoke-test/recent`.

### Why this matters

Without this, the only way to verify a fresh live integration is to wait for your first real customer — and discover only at that point that the webhook secret is wrong or the refund flow is broken. With this, you confirm the pipeline before risking real revenue.

---

## 8. (Optional) Regular E2E smoke test

After major env changes (rotating keys, swapping webhook secret), re-run the smoke test from step 7. It's idempotent and free.

## 9. (Optional) Set up Stripe Tax / VAT

- Stripe dashboard → **Tax → Settings** → enable for jurisdictions you sell into
- This is automatic — no code change required

---

## Rollback

If anything misbehaves, instantly revert to test mode:

```bash
sudo sed -i 's|^STRIPE_API_KEY=.*|STRIPE_API_KEY="sk_test_[removed]"|' /opt/command-os/backend/.env
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

- **Mode detection:** `backend/routes/payments.py::_stripe_mode()` (sk_live → live, sk_test/sk_test_[removed] → test)
- **Safety gate:** `backend/routes/payments.py::create_checkout()` — raises 503 if live without webhook secret
- **Webhook handler:** `backend/routes/payments.py::stripe_webhook()` — verifies signature via [removed] SDK
- **Readiness probe:** `GET /api/payments/readiness` — returns checklist + gating issues
