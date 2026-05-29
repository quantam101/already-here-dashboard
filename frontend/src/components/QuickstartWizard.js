import { useEffect, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { CheckCircle2, AlertCircle, ArrowRight, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { systemAPI, api } from "../lib/api";
import { toast } from "sonner";

const STORAGE_KEY = "ah_quickstart_completed_v1";

function Row({ ok, label, hint, action }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border border-white/5 bg-black/20">
      <div className="mt-0.5">
        {ok ? (
          <CheckCircle2 className="w-5 h-5 text-green-400" />
        ) : (
          <AlertCircle className="w-5 h-5 text-yellow-400" />
        )}
      </div>
      <div className="flex-1">
        <p className={`text-sm font-medium ${ok ? "text-green-300" : "text-white"}`}>{label}</p>
        {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

export default function QuickstartWizard() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  const { data: status, refetch, isFetching } = useQuery({
    queryKey: ["systemStatus"],
    queryFn: () => systemAPI.status().then((r) => r.data),
    enabled: open,
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const done = window.localStorage.getItem(STORAGE_KEY);
    if (!done) setOpen(true);
  }, []);

  const dismiss = () => {
    window.localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    setOpen(false);
  };

  const runCycle = useMutation({
    mutationFn: () => api.post("/cycle/run"),
    onSuccess: () => {
      toast.success("Cycle completed");
      refetch();
    },
    onError: (err) => toast.error(err?.response?.data?.detail || err.message),
  });

  const steps = [
    {
      title: "Welcome to Already Here Command OS",
      body: (
        <div className="space-y-3 text-sm text-gray-300">
          <p>
            This 30-second wizard makes sure the engine is wired correctly so paid
            checkouts, AI advisors, and the daily auto-cycle all fire on day one.
          </p>
          <p className="text-xs text-gray-500">
            You can re-open this anytime by clicking <span className="text-green-400">Quickstart</span> in
            the sidebar status panel.
          </p>
        </div>
      ),
    },
    {
      title: "Step 1 — Operator access",
      body: status ? (
        <div className="space-y-3">
          <Row
            ok={status.operator_email_set}
            label={
              status.operator_email_set
                ? `Operator email locked: ${status.operator_email_masked}`
                : "Operator email NOT set — dashboard is currently OPEN"
            }
            hint={
              status.operator_email_set
                ? "Only this Google account can log in. Good for production."
                : "Set OPERATOR_EMAIL in backend/.env on the OCI host and restart backend to lock down access. Safe to leave open while developing."
            }
          />
        </div>
      ) : (
        <p className="text-gray-400 text-sm">Loading status…</p>
      ),
    },
    {
      title: "Step 2 — Stripe payment mode",
      body: status ? (
        <div className="space-y-3">
          <Row
            ok={status.stripe_mode === "live" || status.stripe_mode === "test"}
            label={
              status.stripe_mode === "live"
                ? "LIVE mode — real money will be charged"
                : status.stripe_mode === "test"
                ? "TEST mode — use card 4242 4242 4242 4242"
                : "STRIPE_API_KEY missing"
            }
            hint={
              status.stripe_mode === "live"
                ? "Make sure STRIPE_WEBHOOK_SECRET is set so paid events idempotently mirror to the ledger."
                : status.stripe_mode === "test"
                ? "Swap to a sk_live_… key in backend/.env when you're ready to take real payments."
                : "Set STRIPE_API_KEY in backend/.env."
            }
          />
          <Row
            ok={status.stripe_webhook_secret_set}
            label={
              status.stripe_webhook_secret_set
                ? "Webhook secret configured"
                : "Webhook secret NOT set (test mode is fine without it)"
            }
            hint="Required for live mode. Get it from dashboard.stripe.com/webhooks after adding /api/payments/webhook."
          />
        </div>
      ) : null,
    },
    {
      title: "Step 3 — Seed data & LLM",
      body: status ? (
        <div className="space-y-3">
          <Row
            ok={status.llm_key_set}
            label={status.llm_key_set ? "LLM provider key active" : "LLM provider key missing"}
            hint="Powers proposals, books, advisor, scout parsing — vendor-neutral via litellm."
          />
          <Row
            ok={status.is_seeded}
            label={status.is_seeded ? `Database seeded (${status.counts.revenue_streams} streams · ${status.counts.agents} agents · ${status.counts.builds} builds)` : "Database not seeded yet"}
            hint={status.is_seeded ? "You can record real earnings on /proof-of-work." : "Run `python /app/backend/seed_data.py` on the host."}
          />
        </div>
      ) : null,
    },
    {
      title: "Step 4 — Test the auto-cycle",
      body: status ? (
        <div className="space-y-3">
          <Row
            ok={true}
            label={`Daily auto-cycle scheduled @ ${status.daily_cycle_hour_utc}:00 UTC`}
            hint="Scrapes scout → drafts content → queues posting log. Run a one-off below to confirm wiring."
          />
          <Button
            onClick={() => runCycle.mutate()}
            disabled={runCycle.isPending}
            variant="outline"
            className="border-green-500/30 text-green-300 hover:bg-green-500/10 w-full"
            data-testid="quickstart-run-cycle"
          >
            <Sparkles className="w-4 h-4 mr-1.5" />
            {runCycle.isPending ? "Running dry-run cycle…" : "Run a test cycle now"}
          </Button>
          {runCycle.data?.data && (
            <div className="text-xs text-green-400 bg-black/40 border border-green-500/20 rounded-md p-2" data-testid="cycle-result">
              ✓ Cycle ran. Ideas: {runCycle.data.data.ideas_created || 0} · Drafts: {runCycle.data.data.publishing_drafts || 0} · Opportunities: {runCycle.data.data.opportunities_scanned || 0}
            </div>
          )}
        </div>
      ) : null,
    },
    {
      title: "You're ready",
      body: (
        <div className="space-y-3 text-sm text-gray-300">
          <p className="text-green-400 font-medium">All systems green. Pin these to your bookmarks:</p>
          <ul className="space-y-1.5 text-xs text-gray-300">
            <li>• <span className="text-white">/overview</span> — Command Center + Profit Meter</li>
            <li>• <span className="text-white">/scout</span> — find viral content + grant opportunities</li>
            <li>• <span className="text-white">/proof-of-work</span> — record real earnings</li>
            <li>• <span className="text-white">/analytics</span> — AI Advisor + UTM attribution</li>
            <li>• <span className="text-white">/pricing</span> — generate Stripe share-links</li>
          </ul>
          <p className="text-xs text-gray-500">
            Deployment guide: <span className="text-blue-400">/app/DEPLOY-TO-OCI.md</span> (also in your repo).
          </p>
        </div>
      ),
    },
  ];

  const current = steps[step];
  const isLast = step === steps.length - 1;

  return (
    <Dialog open={open} onOpenChange={(v) => v ? setOpen(true) : dismiss()}>
      <DialogContent className="bg-[#0f1419] border-white/10 text-white max-w-lg" data-testid="quickstart-wizard">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="text-white">{current.title}</DialogTitle>
            <button
              onClick={dismiss}
              className="text-gray-500 hover:text-white"
              data-testid="quickstart-dismiss"
              aria-label="Dismiss wizard"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <DialogDescription className="text-gray-400 text-xs">
            Step {step + 1} of {steps.length} · One-time setup check
          </DialogDescription>
        </DialogHeader>

        <div className="py-2 min-h-[160px]">{current.body}</div>

        <div className="flex items-center justify-between border-t border-white/10 pt-3">
          <button
            onClick={dismiss}
            className="text-xs text-gray-500 hover:text-white"
            data-testid="quickstart-skip"
          >
            Skip — I know what I'm doing
          </button>
          <div className="flex items-center gap-2">
            {step > 0 && (
              <Button
                variant="outline"
                onClick={() => setStep(step - 1)}
                className="border-white/10 text-gray-300 hover:bg-white/5"
                data-testid="quickstart-back"
              >
                Back
              </Button>
            )}
            <Button
              onClick={() => isLast ? dismiss() : setStep(step + 1)}
              disabled={isFetching}
              className="bg-green-600 hover:bg-green-700 text-white"
              data-testid="quickstart-next"
            >
              {isLast ? "Let's go" : "Next"}
              {!isLast && <ArrowRight className="w-4 h-4 ml-1.5" />}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
