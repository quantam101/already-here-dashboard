import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, XCircle, Clock, ArrowRight } from "lucide-react";
import { paymentsAPI } from "../lib/api";
import { Button } from "@/components/ui/button";

const MAX_ATTEMPTS = 10;
const POLL_INTERVAL_MS = 2000;

export default function PaymentSuccess() {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const navigate = useNavigate();
  const [state, setState] = useState({ status: "checking", data: null, attempts: 0 });

  useEffect(() => {
    if (!sessionId) {
      setState({ status: "no_session", data: null, attempts: 0 });
      return;
    }

    let cancelled = false;
    let attempt = 0;

    const poll = async () => {
      if (cancelled) return;
      attempt += 1;
      try {
        const res = await paymentsAPI.status(sessionId);
        const d = res.data;
        setState({ status: d.payment_status, data: d, attempts: attempt });
        if (d.payment_status === "paid" || d.status === "expired" || attempt >= MAX_ATTEMPTS) return;
      } catch (e) {
        const code = e?.response?.status;
        // Hard-fail (404 / 4xx not transient) - stop polling and surface error
        if (code && code >= 400 && code < 500) {
          setState({ status: "error", data: { error: e?.response?.data?.detail || e.message }, attempts: attempt });
          return;
        }
        setState({ status: "error", data: { error: e.message }, attempts: attempt });
        if (attempt >= MAX_ATTEMPTS) return;
      }
      setTimeout(poll, POLL_INTERVAL_MS);
    };
    poll();
    return () => { cancelled = true; };
  }, [sessionId]);

  const isPaid = state.status === "paid";
  const isExpired = state.data?.status === "expired";
  const isError = state.status === "error";

  return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center p-6" data-testid="payment-success-page">
      <div className="enterprise-card max-w-lg w-full text-center">
        {isPaid && (
          <>
            <CheckCircle2 className="w-16 h-16 text-green-400 mx-auto mb-4" data-testid="payment-success-icon" />
            <h1 className="text-3xl font-bold text-white mb-2">Payment Successful</h1>
            <p className="text-gray-400 mb-6">
              ${state.data?.amount_total?.toFixed(2)} {state.data?.currency?.toUpperCase()} recorded to the revenue ledger.
              {state.data?.ledger_entry_id && (
                <>
                  <br />
                  <span className="text-xs text-green-400 font-mono">
                    Ledger entry: {state.data.ledger_entry_id}
                  </span>
                </>
              )}
            </p>
            <div className="flex flex-col gap-2">
              <Button onClick={() => navigate("/proof-of-work")}
                className="bg-green-600 hover:bg-green-700 text-white"
                data-testid="goto-proof-of-work">
                View Proof of Work <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
              <Button onClick={() => navigate("/overview")} variant="ghost" className="text-gray-400">
                Back to Command Center
              </Button>
            </div>
          </>
        )}
        {!isPaid && !isExpired && !isError && (
          <>
            <Clock className="w-16 h-16 text-yellow-400 mx-auto mb-4 animate-pulse" />
            <h1 className="text-2xl font-bold text-white mb-2">Processing payment...</h1>
            <p className="text-gray-400 mb-4">Polling status (attempt {state.attempts}/{MAX_ATTEMPTS})</p>
            <p className="text-xs text-gray-500 font-mono">Session: {sessionId?.slice(0, 40)}...</p>
          </>
        )}
        {isError && (
          <>
            <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" data-testid="payment-error-icon" />
            <h1 className="text-2xl font-bold text-white mb-2">Status check failed</h1>
            <p className="text-gray-400 mb-6 text-sm">{state.data?.error || "Unknown error"}</p>
            <Button onClick={() => navigate("/pricing")} className="bg-blue-600 hover:bg-blue-700 text-white">
              Back to Pricing
            </Button>
          </>
        )}
        {isExpired && (
          <>
            <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-white mb-2">Session Expired</h1>
            <p className="text-gray-400 mb-6">Please try again.</p>
            <Button onClick={() => navigate("/pricing")} className="bg-blue-600 hover:bg-blue-700 text-white">
              Back to Pricing
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
