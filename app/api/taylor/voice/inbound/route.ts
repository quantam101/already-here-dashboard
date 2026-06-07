import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const operatorNumber = process.env.TAYLOR_OPERATOR_TRANSFER_NUMBER;

type TaylorVoiceIntent = 'initial' | 'schedule' | 'payment' | 'deposit' | 'operator';

export async function GET() {
  return NextResponse.json({
    ok: true,
    service: 'Taylor inbound voice webhook',
    status: 'ready_for_carrier_post',
    accepts: ['POST application/x-www-form-urlencoded from a Twilio-compatible carrier'],
    webhookPath: '/api/taylor/voice/inbound',
    operatorTransferConfigured: Boolean(operatorNumber)
  });
}

export async function POST(request: Request) {
  const bodyText = await request.text();
  const form = new URLSearchParams(bodyText);
  const speechResult = normalizeSpeech(form.get('SpeechResult'));
  const digits = normalizeSpeech(form.get('Digits'));
  const intent = classifyIntent(`${speechResult} ${digits}`);

  return new NextResponse(buildTwiML(intent), {
    status: 200,
    headers: {
      'Content-Type': 'text/xml; charset=utf-8',
      'Cache-Control': 'no-store'
    }
  });
}

function classifyIntent(input: string): TaylorVoiceIntent {
  const value = input.toLowerCase();

  if (!value.trim()) return 'initial';
  if (value.includes('schedule') || value.includes('appointment') || value.includes('service')) return 'schedule';
  if (value.includes('invoice') || value.includes('pay') || value.includes('payment')) return 'payment';
  if (value.includes('deposit') || value.includes('down payment') || value.includes('retainer')) return 'deposit';
  if (value.includes('operator') || value.includes('person') || value.includes('help')) return 'operator';

  return 'operator';
}

function buildTwiML(intent: TaylorVoiceIntent): string {
  const response = twimlResponseForIntent(intent);
  return `<?xml version="1.0" encoding="UTF-8"?><Response>${response}</Response>`;
}

function twimlResponseForIntent(intent: TaylorVoiceIntent): string {
  if (intent === 'schedule') {
    return `${say('I can help schedule service. I will collect the service type and route this for availability review.')}${gather('Please say the service type, service address, and preferred day.')}${fallbackTransfer()}`;
  }

  if (intent === 'payment') {
    return `${say('I can help with invoice payment. For security, payment details are completed only through Stripe secure checkout. Please say the invoice number, billing zip, and amount shown on the invoice.')}${gather('Please provide the invoice number, billing zip, and amount shown on the invoice.')}${fallbackTransfer()}`;
  }

  if (intent === 'deposit') {
    return `${say('I can help with a service deposit or project down payment. For security, I will send a Stripe secure payment link by text or email.')}${gather('Please say the service type, deposit amount, and whether you want the link by text or email.')}${fallbackTransfer()}`;
  }

  if (intent === 'operator') {
    return `${say('I am connecting you with operations now.')}${transferOrHangup()}`;
  }

  return `${gather('Thanks for calling Already Here. This is Taylor. Are we scheduling service, paying an invoice, or making a service deposit today')}${say('I did not receive a clear response. I am routing this to operations.')}${transferOrHangup()}`;
}

function gather(prompt: string): string {
  return `<Gather input="speech dtmf" timeout="6" speechTimeout="auto" action="/api/taylor/voice/inbound" method="POST">${say(prompt)}</Gather>`;
}

function say(text: string): string {
  return `<Say voice="Polly.Joanna-Neural">${escapeXml(text)}</Say>`;
}

function fallbackTransfer(): string {
  return `${say('I am routing this to operations for follow up.')}${transferOrHangup()}`;
}

function transferOrHangup(): string {
  if (!operatorNumber) return '<Hangup/>';
  return `<Dial>${escapeXml(operatorNumber)}</Dial>`;
}

function normalizeSpeech(value: string | null): string {
  return (value ?? '').replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 500);
}

function escapeXml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}
