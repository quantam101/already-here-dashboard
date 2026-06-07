# Taylor Voice Operations and Hosted Stripe Payment Architecture

## Review Grade

Submitted design grade: C+

Corrected production design grade: A

The submitted design has a strong intent around voice automation, failover, agent separation, and fast payment routing. The critical defect is that it attempted to make the voice system handle sensitive payment credentials directly. That is not the correct deployment model for Already Here LLC.

## Correct Payment Rule

Taylor must never collect sensitive card credentials by voice.

Taylor can take payments by verifying the invoice and sending the customer to a Stripe hosted payment experience.

Approved payment paths:

1. Stripe hosted invoice page
2. Stripe Payment Link
3. Stripe Checkout Session
4. Stripe Payment Element when payment entry stays inside Stripe controlled UI
5. Existing payment method on file only after customer authorization and secure server verification

Rejected payment path:

- AI voice agent collects payment credentials and forwards them into an internal API.

## Correct Production Flow

```text
Caller asks to pay
Taylor verifies invoice number, name, amount, and billing ZIP
Taylor creates or retrieves a Stripe hosted payment URL
Taylor sends the secure Stripe payment URL by SMS or email
Customer completes payment on Stripe hosted or Stripe controlled UI
Stripe webhook confirms the payment event
Already Here system marks invoice paid
Taylor confirms receipt only after verified payment status
```

## Taylor State Machine

### INITIAL_GREETING

Taylor says:

Thanks for calling Already Here. This is Taylor. Are we scheduling service or paying an invoice today

### SCHEDULING

Taylor checks availability and offers two service windows.

Rules:

- Do not overbook.
- Do not promise a technician until the system confirms capacity.
- If scheduling services are unavailable, create a callback task and transfer if urgent.

### INVOICE_VERIFICATION

Taylor verifies:

- invoice number
- billing ZIP
- stated amount
- caller delivery preference
- SMS or email destination

Taylor must not ask the caller to speak payment card credentials.

### HOSTED_PAYMENT_LINK

Taylor creates or retrieves the hosted Stripe payment URL and sends it to the verified destination.

Taylor says:

I sent the secure Stripe payment link. For your protection, payment details are entered only on Stripe secure checkout.

### PAYMENT_CONFIRMATION

Taylor confirms payment only after Stripe webhook or secure server lookup verifies the payment.

If not verified yet, Taylor says:

The payment is still pending verification. I will confirm once Stripe reports it as paid.

### OPERATOR_TRANSFER

If any safety gate, provider issue, or unclear request occurs, Taylor transfers the call to operations.

## Agent Mesh

### Voice Agent

Owns conversation routing, appointment intent, invoice intent, delivery preference, and operator transfer.

### Payment Agent

Owns invoice verification, Stripe hosted payment session creation, payment status lookup, and webhook event handling.

### Scheduling Agent

Owns calendar availability, technician capacity, route density, appointment confirmation, and scheduling fallback.

### Dispatch Agent

Owns right-fit technician matching, senior-capacity preservation, project lead routing, and multi-state team coordination.

### Compliance Agent

Owns payment safety rules, secret handling, webhook verification, log redaction, abuse detection, and approval gates.

### Recovery Agent

Owns provider failover, safe task queueing, live operator transfer, and duplicate-action prevention.

## Failover Rules

### Payment provider unavailable

- Do not collect payment credentials by voice.
- Create a payment follow-up task.
- Offer to send the hosted payment link when service is restored.
- Transfer to operations if urgent.

### Calendar unavailable

- Do not confirm a service appointment.
- Collect preferred window.
- Queue manual scheduling review.
- Send confirmation only after capacity is verified.

### Voice platform unavailable

- Play static local message.
- Transfer to operations line.
- Preserve call metadata only.

### Payment webhook delayed

- Do not claim the invoice is paid.
- State that payment is pending verification.
- Confirm only after verified payment status.

## Required Secret Names

```text
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
APP_BASE_URL
TAYLOR_OPERATOR_TRANSFER_NUMBER
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_MESSAGING_SERVICE_SID
CALENDAR_PROVIDER
CALENDAR_SERVICE_ACCOUNT_SECRET
```

No secret key may be committed to GitHub, stored in client-side code, spoken by the voice agent, or embedded in a downloadable ZIP.

## Stripe Readiness Checklist

- Stripe account active
- Business identity verified
- Live mode enabled
- Payment methods enabled in Stripe Dashboard
- Hosted Checkout, Payment Link, or Invoice flow selected
- HTTPS webhook endpoint deployed
- Webhook signature verification implemented
- Secret keys stored only in Vercel or Oracle secrets
- Test mode payment completed
- Owner-approved live test completed
- Refund path tested
- Duplicate payment protection tested
- Voice prompt blocks spoken credential capture

## Production Boundary

This architecture is production ready only after live Stripe credentials, webhook endpoint, business verification, phone carrier configuration, calendar access, operator transfer number, and live payment testing are completed.

Until those are configured, the correct status is production designed and deployment ready, not live payment enabled.
