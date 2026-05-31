/**
 * TokenForge LLM proxy client — free tier (50k tokens/month)
 * Reads REACT_APP_TOKENFORGE_API_KEY from CRA env or falls back to
 * TOKENFORGE_API_KEY for server-side / Node contexts.
 */
const TF_API = 'https://api.tokenforge.io/api/proxy/chat';
const TF_STATUS = 'https://api.tokenforge.io/api/status';

function getApiKey() {
  return (
    (typeof process !== 'undefined' &&
      (process.env.REACT_APP_TOKENFORGE_API_KEY || process.env.TOKENFORGE_API_KEY)) ||
    null
  );
}

export async function tokenforgeChat({ prompt, provider = 'anthropic', model = 'claude-haiku-4-5-20251001', max_tokens = 256 }) {
  const apiKey = getApiKey();
  if (!apiKey) throw new Error('TOKENFORGE_API_KEY not set');
  const res = await fetch(TF_API, {
    method: 'POST',
    headers: { 'X-TF-Key': apiKey, 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, provider, model, max_tokens }),
  });
  if (!res.ok) throw new Error(`TokenForge error ${res.status}`);
  return res.json();
}

export async function tokenforgeStatus() {
  const apiKey = getApiKey();
  if (!apiKey) return { ok: false, error: 'TOKENFORGE_API_KEY not set' };
  try {
    const res = await fetch(TF_STATUS, { headers: { 'X-TF-Key': apiKey } });
    return { ok: res.ok, key_prefix: apiKey.slice(0, 12) + '...', ...(await res.json()) };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}
