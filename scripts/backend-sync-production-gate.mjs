const target = process.env.FIELD_NETWORK_BACKEND_SYNC_URL || 'https://already-here-dashboard.vercel.app/api/backend-sync/status';
const strict = ['1', 'true', 'yes'].includes((process.env.BACKEND_SYNC_STRICT || '').toLowerCase());

function finishDegraded(message) {
  if (strict) {
    console.error(`${message} BACKEND_SYNC_STRICT=true, failing gate.`);
    process.exit(1);
  }

  console.warn(`${message} Reporting DEGRADED without failing CI. Set BACKEND_SYNC_STRICT=true to make this blocking.`);
  process.exit(0);
}

async function main() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(target, {
      signal: controller.signal,
      headers: { 'user-agent': 'field-network-backend-sync-gate/1.1' }
    });

    const text = await response.text();
    let payload;
    try {
      payload = JSON.parse(text);
    } catch {
      return finishDegraded(`Backend sync endpoint did not return JSON. HTTP ${response.status}. Body: ${text.slice(0, 200)}`);
    }

    const connected = response.ok && payload.ok === true && payload.status === 'connected';
    if (!connected) {
      return finishDegraded(`Backend sync not connected. HTTP ${response.status}. Payload: ${JSON.stringify(payload)}`);
    }

    console.log(`Backend sync connected: ${target}`);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return finishDegraded(`Backend sync endpoint unreachable: ${message}`);
  } finally {
    clearTimeout(timeout);
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  finishDegraded(`Backend sync gate unexpected error: ${message}`);
});
