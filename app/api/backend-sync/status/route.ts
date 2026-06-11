import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

function enabled(value: string | undefined): boolean {
  return value === 'true' || value === '1' || value === 'yes';
}

export async function GET() {
  const baseUrl = process.env.ORACLE_API_BASE_URL;
  const syncEnabled = enabled(process.env.SYNC_ENABLED) || Boolean(baseUrl);

  if (!syncEnabled) {
    return NextResponse.json(
      {
        ok: false,
        service: 'backend-sync',
        status: 'disabled',
        connected: false,
        reason: 'Oracle backend URL is not available to the Vercel production runtime.',
        timestamp: new Date().toISOString()
      },
      { status: 503 }
    );
  }

  if (!baseUrl) {
    return NextResponse.json(
      {
        ok: false,
        service: 'backend-sync',
        status: 'misconfigured',
        connected: false,
        missing: { ORACLE_API_BASE_URL: true },
        timestamp: new Date().toISOString()
      },
      { status: 503 }
    );
  }

  try {
    const response = await fetch(`${baseUrl.replace(/\/$/, '')}/health`, {
      headers: { 'user-agent': 'already-here-field-network-os/1.0' },
      cache: 'no-store'
    });

    return NextResponse.json(
      {
        ok: response.ok,
        service: 'backend-sync',
        status: response.ok ? 'connected' : 'degraded',
        connected: response.ok,
        upstreamStatus: response.status,
        timestamp: new Date().toISOString()
      },
      { status: response.ok ? 200 : 502 }
    );
  } catch {
    return NextResponse.json(
      {
        ok: false,
        service: 'backend-sync',
        status: 'unreachable',
        connected: false,
        timestamp: new Date().toISOString()
      },
      { status: 502 }
    );
  }
}
