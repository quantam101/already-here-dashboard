import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { authAPI } from "../lib/api";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
const EMERGENT_AUTH_URL = "https://auth.emergentagent.com/";

function LoginScreen() {
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const handleLogin = () => {
    const redirectUrl = window.location.origin + "/overview";
    window.location.href = `${EMERGENT_AUTH_URL}?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center p-6">
      <div className="enterprise-card max-w-md w-full text-center">
        <h1 className="text-3xl font-bold text-white mb-2">Already Here Command OS</h1>
        <p className="text-gray-400 mb-6 text-sm">Operator access required.</p>
        <button
          onClick={handleLogin}
          className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-lg transition-colors"
          data-testid="login-button"
        >
          Continue with Google
        </button>
        <p className="text-xs text-gray-500 mt-4">
          Only the configured operator email can access the dashboard.
        </p>
      </div>
    </div>
  );
}

export default function AuthGate({ children }) {
  const [state, setState] = useState({ checked: false, required: false, authed: false });
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // CRITICAL: If returning from OAuth callback, skip the /me check.
    // The session_id fragment is handled below.
    if (window.location.hash?.includes("session_id=")) {
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const cfg = await authAPI.config().then((r) => r.data);
        if (!cfg.required) {
          if (!cancelled) setState({ checked: true, required: false, authed: true });
          return;
        }
        try {
          await authAPI.me();
          if (!cancelled) setState({ checked: true, required: true, authed: true });
        } catch {
          if (!cancelled) setState({ checked: true, required: true, authed: false });
        }
      } catch {
        // If the auth config endpoint itself errors, fall open (legacy behavior).
        if (!cancelled) setState({ checked: true, required: false, authed: true });
      }
    })();
    return () => { cancelled = true; };
  }, [location.pathname]);

  // Handle OAuth callback hash
  useEffect(() => {
    if (!window.location.hash?.includes("session_id=")) return;
    const m = window.location.hash.match(/session_id=([^&]+)/);
    const sid = m?.[1];
    if (!sid) return;
    (async () => {
      try {
        await authAPI.session(sid);
        // Strip the fragment and re-route cleanly
        window.history.replaceState({}, "", window.location.pathname);
        setState({ checked: true, required: true, authed: true });
        navigate("/overview", { replace: true });
      } catch (e) {
        setState({ checked: true, required: true, authed: false });
      }
    })();
  }, [navigate]);

  if (!state.checked) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center text-gray-400 text-sm">
        Loading…
      </div>
    );
  }
  if (state.required && !state.authed) {
    return <LoginScreen />;
  }
  return children;
}
