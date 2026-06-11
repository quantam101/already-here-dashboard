import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

function pickEnv(names: string[]): string | undefined {
  for (const name of names) {
    const value = process.env[name]?.trim();
    if (value) return value;
  }
  return undefined;
}

function enabled(value: string | undefined): boolean {
  return value === 'true' || value === '1' || value === 'yes';
}

export async function GET() {
  const baseUrl = pickEnv([
    'ORACLE_API_BASE_URL',
    'NEXT_PUBLIC_ORACLE_API_BASE_URL',
    'FIELD_NETWORK_BACKEND_URL',
    'FIELD_NETWORK_API_URL',
    'BACKEND_API_URL',
    'API_BASE_URL'
  ]);
  const syncEnabled = enabled(process.env.SYNC_ENABLED) || Boolean(baseUrl);

  if (!syncEnabled) {
    return NextResponse.json(
      {
        ok: false,
        service: 'backend-sync',
        status: 'disabled',
        connected: false,
        reason: 'No supported backend API URL is available to the Vercel production runtime.',
        acceptedEnvNames: [
          'ORACLE_API_BASE_URL',
          'NEXT_PUBLIC_ORACLE_API_BASE_URL',
          'FIELD_NETWORK_BACKEND_URL',
          'FIELD_NETWORK_API_URL',
          'BACKEND_API_URL',
          'API_BASE_URL'
        ],
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
