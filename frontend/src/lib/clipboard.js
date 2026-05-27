// Clipboard utility that works in restricted iframes (like Emergent preview).
//
// The native navigator.clipboard.writeText() requires the "clipboard-write"
// permissions policy, which iframes often block. This helper:
//   1. Tries navigator.clipboard first (works in production / direct-loaded app)
//   2. Falls back to the document.execCommand('copy') textarea trick
//      (works inside permissions-restricted iframes)
//   3. Returns a Promise<boolean> so callers can show success/failure toasts
//
// Usage:
//   import { copyToClipboard } from "../lib/clipboard";
//   copyToClipboard(text).then(ok => toast[ok ? "success" : "error"](...));

export async function copyToClipboard(text) {
  if (!text) return false;

  // Path 1 — modern async clipboard API
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (_e) {
    // fall through to legacy
  }

  // Path 2 — legacy textarea + execCommand (works in restricted iframes)
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "0";
    ta.style.left = "0";
    ta.style.opacity = "0";
    ta.style.pointerEvents = "none";
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, ta.value.length);
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch (_e) {
    return false;
  }
}

// Open a URL in a new tab. In permissions-restricted iframes window.open can
// return null — we surface that to the caller so they can fall back to
// showing the URL in a toast/dialog for manual click.
export function openInNewTab(url) {
  if (!url) return false;
  try {
    const win = window.open(url, "_blank", "noopener,noreferrer");
    return !!win;
  } catch (_e) {
    return false;
  }
}
