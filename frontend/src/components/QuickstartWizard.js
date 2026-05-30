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

  // Auto-open disabled — FirstRunWalkthrough is now the primary first-run experience.
  // QuickstartWizard remains available as a secondary system-check via the sidebar trigger.
  useEffect(() => {
    if (typeof window === "undefined") return;
    window.ahOpenQuickstart = () => { setStep(0); setOpen(true); };
    return () => { delete window.ahOpenQuickstart; };
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
            This wizard walks you through the 5-step setup so autonomous content posting,
            AI advisors, and the daily auto-cycle all fire on day one — with{" "}
            <span className="text-green-400 font-semibold">$0/month fixed cost</span>.
          </p>
          <div className="bg-black/30 border border-white/5 rounded-lg p-3 space-y-1.5 text-xs">
            <p className="text-green-400 font-semibold">What happens automatically once configured:</p>
            <p>✦ Daily Scout scans Reddit, HN, Google News for viral topics</p>
            <p>✦ AI writes article + video script for every trending idea</p>
            <p>✦ Auto-posts to Medium, Dev.to, Reddit, LinkedIn, Facebook, Threads</p>
            <p>✦ Generates CapCut-ready scripts for TikTok / YouTube Shorts / Reels</p>
            <p>✦ Export packs for Facebook Groups, Quora, niche forums</p>
          </div>
          <p className="text-xs text-gray-500">
            Re-open anytime via <span className="text-green-400">Re-open Quickstart</span> in the sidebar.
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
      title: "Step 4 — Connect social platforms",
      body: (
        <div className="space-y-3">
          <p className="text-xs text-gray-400">
            Add credentials to your server <code className="text-green-400 bg-black/30 px-1 rounded">/opt/command-os/.env</code> then restart the backend.
            Each takes 5–15 minutes. Start with Tier 1 — they work today without app review.
          </p>
          <div className="space-y-2">
            <div className="bg-black/30 border border-green-500/20 rounded-lg p-2.5">
              <p className="text-xs font-semibold text-green-400 mb-1">✅ Tier 1 — Works Today (5–15 min each)</p>
              <div className="space-y-1 text-xs text-gray-300">
                <p><span className="text-white">Medium:</span> medium.com/me/settings/security → Integration token → <code className="text-green-400">MEDIUM_INTEGRATION_TOKEN</code></p>
                <p><span className="text-white">Dev.to:</span> dev.to/settings/extensions → API key → <code className="text-green-400">DEVTO_API_KEY</code></p>
                <p><span className="text-white">Reddit:</span> reddit.com/prefs/apps → "script" app → <code className="text-green-400">REDDIT_CLIENT_ID / SECRET / USERNAME / PASSWORD</code></p>
              </div>
            </div>
            <div className="bg-black/30 border border-yellow-500/20 rounded-lg p-2.5">
              <p className="text-xs font-semibold text-yellow-400 mb-1">🟡 Tier 2 — Needs App Registration (1–4 hrs)</p>
              <div className="space-y-1 text-xs text-gray-300">
                <p><span className="text-white">LinkedIn:</span> linkedin.com/developers → <code className="text-green-400">LINKEDIN_ACCESS_TOKEN + LINKEDIN_PERSON_URN</code></p>
                <p><span className="text-white">YouTube:</span> Google Cloud Console → YouTube Data API v3 → OAuth2 → <code className="text-green-400">YOUTUBE_CLIENT_ID / SECRET / REFRESH_TOKEN</code></p>
              </div>
            </div>
            <div className="bg-black/30 border border-red-500/20 rounded-lg p-2.5">
              <p className="text-xs font-semibold text-red-400 mb-1">🔴 Tier 3 — App Review Required (days–weeks)</p>
              <div className="space-y-1 text-xs text-gray-300">
                <p><span className="text-white">Facebook + Instagram + Threads:</span> developers.facebook.com → one Meta app → <code className="text-green-400">FB_PAGE_ACCESS_TOKEN / IG_ACCESS_TOKEN / THREADS_ACCESS_TOKEN</code></p>
                <p><span className="text-white">TikTok:</span> developers.tiktok.com → Content Posting API approval → <code className="text-green-400">TIKTOK_ACCESS_TOKEN</code></p>
              </div>
            </div>
          </div>
          <p className="text-xs text-gray-500">
            Full guide: <span className="text-blue-400">SOCIAL_SETUP.md</span> in your repo. Check live status at{" "}
            <code className="text-green-400 bg-black/30 px-1 rounded">/api/cycle/connectors</code>
          </p>
        </div>
      ),
    },
    {
      title: "📹 Faceless Video Creation — How It Works",
      body: (
        <div className="space-y-3">
          <p className="text-xs text-gray-400">
            You never appear on camera. The system does the thinking; CapCut does the editing.
          </p>
          <div className="space-y-2 text-xs">
            <div className="flex gap-3 p-2.5 rounded-lg bg-black/30 border border-white/5">
              <span className="text-green-400 font-bold text-base leading-none mt-0.5">1</span>
              <div>
                <p className="text-white font-semibold">AI writes the script</p>
                <p className="text-gray-400">Scout finds a trending topic → AI generates hook + narration sections + CTA. Go to <span className="text-green-400">Content Factory</span> → pick any idea → click <span className="text-green-400">Generate Script</span>.</p>
              </div>
            </div>
            <div className="flex gap-3 p-2.5 rounded-lg bg-black/30 border border-white/5">
              <span className="text-green-400 font-bold text-base leading-none mt-0.5">2</span>
              <div>
                <p className="text-white font-semibold">Get the Export Pack</p>
                <p className="text-gray-400">Click <span className="text-green-400">Export Pack</span> on any idea. You get a formatted <span className="text-white">video_script</span> with hook, bullet narration, and CTA — plus captions and hashtags pre-written.</p>
              </div>
            </div>
            <div className="flex gap-3 p-2.5 rounded-lg bg-black/30 border border-white/5">
              <span className="text-green-400 font-bold text-base leading-none mt-0.5">3</span>
              <div>
                <p className="text-white font-semibold">Film in CapCut (free)</p>
                <p className="text-gray-400">Use CapCut's AI text-to-speech (free tier) to narrate. Add stock footage from their library. Export as 9:16 vertical for TikTok/Shorts/Reels or 16:9 for full YouTube.</p>
              </div>
            </div>
            <div className="flex gap-3 p-2.5 rounded-lg bg-black/30 border border-white/5">
              <span className="text-green-400 font-bold text-base leading-none mt-0.5">4</span>
              <div>
                <p className="text-white font-semibold">Post &amp; mark as done</p>
                <p className="text-gray-400">Upload manually via TikTok / YouTube Studio / Instagram, or configure API tokens for auto-upload. Mark as posted in <span className="text-green-400">Publishing</span> to track analytics.</p>
              </div>
            </div>
          </div>
        </div>
      ),
    },
    {
      title: "Step 5 — Test the auto-cycle",
      body: status ? (
        <div className="space-y-3">
          <Row
            ok={true}
            label={`Daily auto-cycle scheduled @ ${status.daily_cycle_hour_utc}:00 UTC`}
            hint="Scouts trending topics → writes scripts → auto-posts to configured text platforms → generates Export Packs for video/manual. Run a one-off below to confirm everything is wired."
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
            <div className="text-xs text-green-400 bg-black/40 border border-green-500/20 rounded-md p-2 space-y-1" data-testid="cycle-result">
              <p>✓ Cycle ran. Ideas: {runCycle.data.data.ideas_created || 0} · Drafts: {runCycle.data.data.publishing_drafts || 0} · Opportunities: {runCycle.data.data.opportunities_scanned || 0}</p>
              {runCycle.data.data.auto_posted > 0 && (
                <p>🚀 Auto-posted to: {runCycle.data.data.live_connectors?.join(", ") || "configured platforms"}</p>
              )}
              {runCycle.data.data.export_packs > 0 && (
                <p>📦 Export packs ready — go to Content Factory → any idea → Export Pack</p>
              )}
              {runCycle.data.data.auto_posted === 0 && runCycle.data.data.export_packs > 0 && (
                <p className="text-yellow-400">⚠ No social credentials configured yet — add them in Step 4 above</p>
              )}
            </div>
          )}
        </div>
      ) : null,
    },
    {
      title: "You're live 🚀",
      body: (
        <div className="space-y-3 text-sm text-gray-300">
          <p className="text-green-400 font-medium">Command OS is fully operational. Your daily workflow:</p>
          <div className="bg-black/30 border border-white/5 rounded-lg p-3 space-y-1.5 text-xs">
            <p className="text-white font-semibold">Every morning (automated):</p>
            <p className="text-gray-400">Scout finds viral ideas → AI writes scripts → posts to text platforms → export packs generated for video</p>
            <p className="text-white font-semibold mt-2">Your 10-minute video routine:</p>
            <p className="text-gray-400">Content Factory → pick top idea → Export Pack → copy video_script → CapCut → film with TTS → post</p>
          </div>
          <div className="grid grid-cols-2 gap-1.5 text-xs">
            <div className="bg-black/30 border border-white/5 rounded p-2">
              <p className="text-white font-semibold mb-0.5">Key pages</p>
              <p className="text-gray-400">/studio — Content Factory</p>
              <p className="text-gray-400">/scout — Viral ideas</p>
              <p className="text-gray-400">/sovereign — Cash AI advisor</p>
            </div>
            <div className="bg-black/30 border border-white/5 rounded p-2">
              <p className="text-white font-semibold mb-0.5">Revenue tracking</p>
              <p className="text-gray-400">/proof-of-work — log income</p>
              <p className="text-gray-400">/analytics — UTM + ROI</p>
              <p className="text-gray-400">/pricing — Stripe links</p>
            </div>
          </div>
          <p className="text-xs text-gray-500">
            Deployment guide: <span className="text-blue-400">/app/DEPLOY-NOW.md</span> (also in your repo).
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
