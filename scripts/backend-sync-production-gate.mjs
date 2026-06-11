const target = process.env.FIELD_NETWORK_BACKEND_SYNC_URL || 'https://field.alreadyherellc.com/api/backend-sync/status';

async function main() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(target, {
      signal: controller.signal,
      headers: { 'user-agent': 'field-network-backend-sync-gate/1.0' }
    });
    const text = await response.text();
    let payload;
    try {
      payload = JSON.parse(text);
    } catch {
      throw new Error(`Backend sync endpoint did not return JSON. HTTP ${response.status}. Body: ${text.slice(0, 200)}`);
    }

    if (!response.ok || payload.ok !== true || payload.status !== 'connected') {
      throw new Error(`Backend sync not connected. HTTP ${response.status}. Payload: ${JSON.stringify(payload)}`);
    }

    console.log(`Backend sync connected: ${target}`);
  } finally {
    clearTimeout(timeout);
  }
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
