import { NextResponse } from 'next/server';
import { createStripeCheckoutSession, type CreateHostedPaymentInput } from '../../../../lib/stripe-hosted-payments';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const allowedPurposes = new Set([
  'invoice_payment',
  'service_deposit',
  'project_down_payment',
  'retainer_activation',
  'dispatch_reservation',
  'parts_deposit'
]);

export async function POST(request: Request) {
  try {
    const body = await request.json() as Partial<CreateHostedPaymentInput>;
    const parsed = parseRequestBody(body);

    const session = await createStripeCheckoutSession(parsed);

    return NextResponse.json({
      ok: true,
      sessionId: session.id,
      hostedPaymentUrl: session.url,
      paymentStatus: session.paymentStatus,
      status: session.status,
      amountTotal: session.amountTotal,
      taylorSpokenResponse: buildTaylorPaymentResponse(parsed)
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unable to create hosted payment link';
    return NextResponse.json({
      ok: false,
      error: message,
      taylorSpokenResponse: 'I cannot create the secure payment link from here right now. I am routing this to operations.'
    }, { status: 400 });
  }
}

function parseRequestBody(body: Partial<CreateHostedPaymentInput>): CreateHostedPaymentInput {
  const amountCents = Number(body.amountCents);
  const purpose = String(body.purpose ?? 'service_deposit');
  const description = String(body.description ?? '').trim();

  if (!allowedPurposes.has(purpose)) {
    throw new Error('Unsupported payment purpose');
  }

  return {
    amountCents,
    purpose: purpose as CreateHostedPaymentInput['purpose'],
    description,
    customerName: normalizeOptionalString(body.customerName),
    customerEmail: normalizeOptionalString(body.customerEmail),
    customerPhone: normalizeOptionalString(body.customerPhone),
    serviceAddress: normalizeOptionalString(body.serviceAddress),
    serviceType: normalizeOptionalString(body.serviceType),
    invoiceId: normalizeOptionalString(body.invoiceId),
    internalReferenceId: normalizeOptionalString(body.internalReferenceId)
  };
}

function normalizeOptionalString(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function buildTaylorPaymentResponse(input: CreateHostedPaymentInput): string {
  const amount = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(input.amountCents / 100);

  switch (input.purpose) {
    case 'invoice_payment':
      return `I found the payment request for ${amount}. I sent the secure Stripe payment link. Payment is completed on Stripe secure checkout.`;
    case 'project_down_payment':
      return `For this project, the down payment is ${amount}. I sent the secure Stripe payment link. Once Stripe verifies payment, I will update the service record for project review.`;
    case 'retainer_activation':
      return `This payment activates the retainer. The amount is ${amount}. I sent the secure Stripe payment link. Operations will confirm the next service window after payment is verified.`;
    case 'dispatch_reservation':
      return `This payment starts the dispatch review. The amount is ${amount}. I sent the secure Stripe payment link. Final scheduling depends on technician availability and route confirmation.`;
    case 'parts_deposit':
      return `The parts deposit is ${amount}. I sent the secure Stripe payment link. The service record will update after payment is verified.`;
    case 'service_deposit':
    default:
      return `I can reserve the next step with a service deposit. The deposit amount is ${amount}. I sent the secure Stripe payment link.`;
  }
}
