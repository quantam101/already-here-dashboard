export type HostedPaymentPurpose = 'invoice_payment' | 'service_deposit' | 'project_down_payment' | 'retainer_activation' | 'dispatch_reservation' | 'parts_deposit';

export interface CreateHostedPaymentInput {
  amountCents: number;
  purpose: HostedPaymentPurpose;
  description: string;
  customerName?: string;
  customerEmail?: string;
  customerPhone?: string;
  serviceAddress?: string;
  serviceType?: string;
  invoiceId?: string;
  internalReferenceId?: string;
}

export interface HostedPaymentSession {
  id: string;
  url: string;
  paymentStatus: string;
  status: string;
  amountTotal: number;
}

const allowedPurposes: HostedPaymentPurpose[] = [
  'invoice_payment',
  'service_deposit',
  'project_down_payment',
  'retainer_activation',
  'dispatch_reservation',
  'parts_deposit'
];

export function validateHostedPaymentInput(input: CreateHostedPaymentInput): string[] {
  const errors: string[] = [];

  if (!Number.isInteger(input.amountCents) || input.amountCents < 100 || input.amountCents > 2500000) {
    errors.push('amountCents must be an integer between 100 and 2500000');
  }

  if (!allowedPurposes.includes(input.purpose)) {
    errors.push('purpose is not supported');
  }

  if (!input.description || input.description.trim().length < 4 || input.description.length > 160) {
    errors.push('description must be between 4 and 160 characters');
  }

  if (input.customerEmail && !/^\S+@\S+\.\S+$/.test(input.customerEmail)) {
    errors.push('customerEmail is invalid');
  }

  return errors;
}

export function buildCheckoutParams(input: CreateHostedPaymentInput, appBaseUrl: string): URLSearchParams {
  const referenceId = sanitizeMetadataValue(input.internalReferenceId ?? input.invoiceId ?? crypto.randomUUID());
  const description = sanitizeLineItemName(input.description);
  const successUrl = `${trimTrailingSlash(appBaseUrl)}/payment/success?session_id={CHECKOUT_SESSION_ID}`;
  const cancelUrl = `${trimTrailingSlash(appBaseUrl)}/payment/cancelled?ref=${encodeURIComponent(referenceId)}`;

  const params = new URLSearchParams();
  params.set('mode', 'payment');
  params.set('success_url', successUrl);
  params.set('cancel_url', cancelUrl);
  params.set('client_reference_id', referenceId);
  params.set('line_items[0][quantity]', '1');
  params.set('line_items[0][price_data][currency]', 'usd');
  params.set('line_items[0][price_data][unit_amount]', String(input.amountCents));
  params.set('line_items[0][price_data][product_data][name]', description);
  params.set('payment_intent_data[metadata][purpose]', input.purpose);
  params.set('payment_intent_data[metadata][internal_reference_id]', referenceId);
  params.set('metadata[purpose]', input.purpose);
  params.set('metadata[internal_reference_id]', referenceId);

  if (input.invoiceId) params.set('metadata[invoice_id]', sanitizeMetadataValue(input.invoiceId));
  if (input.serviceType) params.set('metadata[service_type]', sanitizeMetadataValue(input.serviceType));
  if (input.serviceAddress) params.set('metadata[service_address]', sanitizeMetadataValue(input.serviceAddress));
  if (input.customerName) params.set('metadata[customer_name]', sanitizeMetadataValue(input.customerName));
  if (input.customerPhone) params.set('metadata[customer_phone]', sanitizeMetadataValue(input.customerPhone));
  if (input.customerEmail) params.set('customer_email', input.customerEmail.trim());

  return params;
}

export async function createStripeCheckoutSession(input: CreateHostedPaymentInput): Promise<HostedPaymentSession> {
  const errors = validateHostedPaymentInput(input);
  if (errors.length > 0) {
    throw new Error(errors.join('; '));
  }

  const stripeSecretKey = process.env.STRIPE_SECRET_KEY;
  const appBaseUrl = process.env.APP_BASE_URL;

  if (!stripeSecretKey) {
    throw new Error('STRIPE_SECRET_KEY is not configured');
  }

  if (!appBaseUrl) {
    throw new Error('APP_BASE_URL is not configured');
  }

  const response = await fetch('https://api.stripe.com/v1/checkout/sessions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${stripeSecretKey}`,
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: buildCheckoutParams(input, appBaseUrl),
    cache: 'no-store'
  });

  const payload = await response.json() as {
    id?: string;
    url?: string;
    payment_status?: string;
    status?: string;
    amount_total?: number;
    error?: { message?: string };
  };

  if (!response.ok || !payload.id || !payload.url) {
    throw new Error(payload.error?.message ?? 'Stripe Checkout Session creation failed');
  }

  return {
    id: payload.id,
    url: payload.url,
    paymentStatus: payload.payment_status ?? 'unpaid',
    status: payload.status ?? 'open',
    amountTotal: payload.amount_total ?? input.amountCents
  };
}

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

function sanitizeLineItemName(value: string): string {
  return value.replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 160);
}

function sanitizeMetadataValue(value: string): string {
  return value.replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 500);
}
