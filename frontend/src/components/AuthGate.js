import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { authAPI } from "../lib/api";
import { toast } from "sonner";

const PUBLIC_PATHS = new Set(["/pricing", "/waitlist", "/payment-success"]);

function LoginScreen({ onSuccess }) {
  const [token, setToken] = useState("");
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!token.trim()) {
      toast.error("Operator token required");
      return;
    }
    setSubmitting(true);
    try {
      await authAPI.login({ operator_token: token.trim(), name: name.trim() || undefined });
      toast.success("Welcome back, operator");
      onSuccess?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Invalid operator token");
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center p-6">
      <form onSubmit={handleSubmit} className="enterprise-card max-w-md w-full">
        <h1 className="text-3xl font-bold text-white mb-2">Command OS</h1>
        <p className="text-gray-400 mb-6 text-sm">
          Operator access required. Enter the OPERATOR_TOKEN from your{" "}
          <code className="text-amber-300">backend/.env</code> file.
        </p>

        <label className="block text-xs uppercase tracking-wider text-gray-400 mb-1">
          Operator token
        </label>
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          autoComplete="current-password"
          placeholder="Paste OPERATOR_TOKEN"
          className="w-full bg-[#0a0e1a] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm mb-3 focus:border-emerald-500 outline-none"
          data-testid="operator-token-input"
        />

        <label className="block text-xs uppercase tracking-wider text-gray-400 mb-1">
          Display name <span className="text-gray-600">(optional)</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Operator"
          className="w-full bg-[#0a0e1a] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm mb-4 focus:border-emerald-500 outline-none"
          data-testid="operator-name-input"
        />

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white font-semibold py-3 rounded-lg transition-colors"
          data-testid="login-button"
        >
          {submitting ? "Authenticating…" : "Sign in"}
        </button>

        <p className="text-[11px] text-gray-500 mt-4 leading-snug">
          Lost your token? Run <code className="text-amber-300">openssl rand -hex 32</code>{" "}
          on the server, paste the output into <code>OPERATOR_TOKEN</code> in{" "}
          <code>backend/.env</code>, restart, and use that.
        </p>
      </form>
    </div>
  );
}

export default function AuthGate({ children }) {
  const [state, setState] = useState({ checked: false, required: false, authed: false });
  const location = useLocation();
  const isPublicPath = PUBLIC_PATHS.has(location.pathname);

  const refresh = async () => {
    try {
      const cfg = await authAPI.config().then((r) => r.data);
      if (!cfg.required) {
        setState({ checked: true, required: false, authed: true });
        return;
      }
      try {
        await authAPI.me();
        setState({ checked: true, required: true, authed: true });
      } catch {
        setState({ checked: true, required: true, authed: false });
      }
    } catch {
      // If the auth config endpoint itself errors, fall open
      setState({ checked: true, required: false, authed: true });
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const cfg = await authAPI.config().then((r) => r.data);
        if (cancelled) return;
        if (!cfg.required) {
          setState({ checked: true, required: false, authed: true });
          return;
        }
        try {
          await authAPI.me();
          if (!cancelled) setState({ checked: true, required: true, authed: true });
        } catch {
          if (!cancelled) setState({ checked: true, required: true, authed: false });
        }
      } catch {
        if (!cancelled) setState({ checked: true, required: false, authed: true });
      }
    })();
    return () => { cancelled = true; };
  }, [location.pathname]);

  if (isPublicPath) {
    return children;
  }

  if (!state.checked) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center text-gray-400 text-sm">
        Loading…
      </div>
    );
  }
  if (state.required && !state.authed) {
    return <LoginScreen onSuccess={refresh} />;
  }
  return children;
}
