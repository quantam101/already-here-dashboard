import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

function enabled(value: string | undefined): boolean {
  return value === 'true' || value === '1' || value === 'yes';
}

export async function GET() {
  const syncEnabled = enabled(process.env.SYNC_ENABLED);
  const baseUrl = process.env.ORACLE_API_BASE_URL;
  const serviceToken = process.env.ORACLE_API_SERVICE_TOKEN;

  if (!syncEnabled) {
    return NextResponse.json(
      {
        ok: false,
        service: 'backend-sync',
        status: 'disabled',
        connected: false,
        reason: 'SYNC_ENABLED is not true',
        timestamp: new Date().toISOString()
      },
      { status: 503 }
    );
  }

  if (!baseUrl || !serviceToken) {
    return NextResponse.json(
      {
        ok: false,
        service: 'backend-sync',
        status: 'misconfigured',
        connected: false,
        missing: {
          ORACLE_API_BASE_URL: !baseUrl,
          ORACLE_API_SERVICE_TOKEN: !serviceToken
        },
        timestamp: new Date().toISOString()
      },
      { status: 503 }
    );
  }

  try {
    const response = await fetch(`${baseUrl.replace(/\/$/, '')}/health`, {
      headers: {
        authorization: `Bearer ${serviceToken}`,
        'user-agent': 'already-here-field-network-os/1.0'
      },
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
