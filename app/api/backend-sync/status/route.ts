import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

const fallbackBaseUrl = 'https://profitenginev5.vercel.app/api';

function pickEnv(names: string[]): string | undefined {
  for (const name of names) {
    const value = process.env[name]?.trim();
    if (value) return value;
  }
  return undefined;
}

export async function GET() {
  const configuredBaseUrl = pickEnv([
    'ORACLE_API_BASE_URL',
    'NEXT_PUBLIC_ORACLE_API_BASE_URL',
    'FIELD_NETWORK_BACKEND_URL',
    'FIELD_NETWORK_API_URL',
    'BACKEND_API_URL',
    'API_BASE_URL'
  ]);
  const baseUrl = configuredBaseUrl || fallbackBaseUrl;
  const targetType = configuredBaseUrl ? 'configured-backend' : 'fallback-control-layer';

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
        targetType,
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
        targetType,
        timestamp: new Date().toISOString()
      },
      { status: 502 }
    );
  }
}
