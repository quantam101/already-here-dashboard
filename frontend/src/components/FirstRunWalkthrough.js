/**
 * ProfitEngine v5 — First-Run Walkthrough
 * 10-step interactive tour. Auto-launches on first visit (gated on
 * localStorage.pe5_walkthrough_seen). Replayable via <TakeTourButton />.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles, X, ChevronLeft, ChevronRight, PartyPopper, Film,
  BookOpen, FileText, Wand2, ShieldCheck, Cpu, Database, Rocket,
  Compass, CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const STORAGE_KEY = "pe5_walkthrough_seen";

const STEPS = [
  {
    icon: PartyPopper,
    title: "Welcome to ProfitEngine v5",
    route: "/overview",
    body: (
      <>
        <p>You're looking at <strong>ProfitEngine v5 — Already Here Command OS</strong>. One operator, multi-agent governance, $0/mo on Oracle Cloud Always Free.</p>
        <p className="mt-3">10 quick stops. Each drops you on the live page and shows the exact 30-second action that lights up that subsystem.</p>
        <p className="mt-3 text-xs text-emerald-300">Press <kbd className="px-1.5 py-0.5 bg-white/10 border border-white/20 rounded">Esc</kbd> to skip. "Take the tour" in the sidebar replays it anytime.</p>
      </>
    ),
  },
  {
    icon: Compass,
    title: "1 — The Command Center",
    route: "/overview",
    body: (
      <>
        <p>Your <strong>Overview</strong> — Master Revenue Equation, agent status, recent activity, governance level.</p>
        <p className="mt-2"><strong>Try right now:</strong> scroll down — you'll see your Revenue Streams, Active Agents, and L5 Governance badges live. Everything is wired to real backend endpoints — nothing mocked.</p>
      </>
    ),
  },
  {
    icon: Film,
    title: "2 — Video Studio + Generative Suite",
    route: "/video-studio",
    body: (
      <>
        <p>The crown jewel. Vertical 1080×1920 renders at $0/mo using:</p>
        <ul className="mt-2 ml-4 list-disc text-sm space-y-1">
          <li><strong>Coqui XTTS-v2</strong> local voice clone (upload 6-30s of your voice)</li>
          <li><strong>transformers MusicGen</strong> local AI music beds</li>
          <li><strong>Pollinations FLUX + HF FLUX-schnell</strong> AI B-roll per shot</li>
          <li><strong>faster-whisper</strong> adaptive word-level captions</li>
        </ul>
        <p className="mt-3"><strong>First-render recipe (~90s):</strong></p>
        <ol className="mt-1 ml-4 list-decimal text-sm space-y-1">
          <li>Scroll to the <em>Generative Suite</em> panel.</li>
          <li>In "Voice clone refs", upload any 10s sample of your voice.</li>
          <li>In "AI music", type <code className="px-1 bg-white/10 rounded">upbeat cinematic build</code>.</li>
          <li>Paste a script (hook / body / CTA / shot list) in the form.</li>
          <li>Click <em>Render Video</em>. Job polls itself green in 30-60s.</li>
        </ol>
      </>
    ),
  },
  {
    icon: BookOpen,
    title: "3 — Books & Audiobooks",
    route: "/books",
    body: (
      <>
        <p>End-to-end authoring: title → chapters → markdown → audiobook.</p>
        <p className="mt-2"><strong>Try right now:</strong> click <em>New Book</em>, pick <code className="px-1 bg-white/10 rounded">guide</code>, 3 chapters, 600 words each. The Gemini fallback chain drafts each chapter.</p>
        <p className="mt-2">Click <em>Generate Audio</em> on the resulting book — Piper TTS renders each chapter as a 22 kHz WAV, then ffmpeg concatenates the audiobook.</p>
      </>
    ),
  },
  {
    icon: FileText,
    title: "4 — Proposals",
    route: "/proposals",
    body: (
      <>
        <p>Capability-statement / RFP-response generator. Input the brief, output a governance-validated draft.</p>
        <p className="mt-2"><strong>Try right now:</strong> click <em>New Proposal</em>, paste an opportunity description, click <em>Draft</em>. The execution_unit agent writes the response; the adversarial_critic reviews it for placeholders.</p>
      </>
    ),
  },
  {
    icon: Wand2,
    title: "5 — Viral Hook A/B Tester",
    route: "/video-studio",
    body: (
      <>
        <p>Generates N hook variants across 6 viral patterns (negation / curiosity-gap / bold-claim / listicle / controversy / pattern-interrupt), then fires <em>N parallel</em> video renders.</p>
        <p className="mt-2"><strong>Try right now:</strong> scroll to the <em>Hook A/B Tester</em> button in Video Studio. Topic + niche → click. You'll see N job rows appear in <em>Recent Renders</em> running in parallel.</p>
        <p className="mt-2 text-xs text-emerald-300">Even when every Gemini bucket is exhausted, the deterministic template fallback still ships valid hooks.</p>
      </>
    ),
  },
  {
    icon: ShieldCheck,
    title: "6 — Governance & Approvals",
    route: "/approvals",
    body: (
      <>
        <p>L0–L5 governance with dual-actor HITL gates. Any autonomous action above policy threshold (capital_allocation / mass_outreach / external_publishing) parks here.</p>
        <p className="mt-2"><strong>Try right now:</strong> the queue shows recent gates. <em>Approve</em> flows it through; <em>Reject</em> logs in the audit trail.</p>
      </>
    ),
  },
  {
    icon: Database,
    title: "7 — Distillation Cache & Cost Guard",
    route: "/audit",
    body: (
      <>
        <p>Every LLM call goes through semantic compression + cache lookup before hitting the provider. Cost Guard tracks per-day burn and fires a HITL gate if a route exceeds its allowance.</p>
        <p className="mt-2"><strong>Watch for:</strong> <code className="px-1 bg-white/10 rounded">cache_hit</code> events grow as the day progresses — repeated prompts cost zero.</p>
      </>
    ),
  },
  {
    icon: Cpu,
    title: "8 — D-ASI Swarm Director (HF Space)",
    route: "/overview",
    body: (
      <>
        <p>Live at <a href="https://alreadyherellc-dasi-kernel.hf.space" target="_blank" rel="noreferrer" className="text-blue-300 underline">alreadyherellc-dasi-kernel.hf.space</a>. Four-agent VHLL DAG on DeepSeek-V3 / Qwen2.5-7B.</p>
        <p className="mt-2"><strong>Try right now:</strong></p>
        <pre className="mt-1 p-2 text-[10px] bg-black/40 border border-white/10 rounded overflow-x-auto"><code>{`SPACE='https://alreadyherellc-dasi-kernel.hf.space'
curl -X POST "$SPACE/matrix/execute" \\
  -H 'Content-Type: application/json' \\
  -d '{"directive":"Output 3 zero-trust API rules. Pure JSON only."}'
sleep 30
curl "$SPACE/matrix/telemetry"`}</code></pre>
        <p className="mt-2 text-xs text-emerald-300">SEC_ZERO_PLACEHOLDER_POLICY blocks any output with ellipses / TODOs / placeholders. Auto-retries up to 3× before halt.</p>
      </>
    ),
  },
  {
    icon: Rocket,
    title: "You're set. Now ship.",
    route: "/overview",
    body: (
      <>
        <p className="text-lg">Daily flow:</p>
        <ul className="mt-3 ml-4 list-disc space-y-1 text-sm">
          <li><strong>One faceless video / day</strong> → <em>Video Studio</em></li>
          <li><strong>One book / week</strong> → <em>Books</em> → generate → audiobook</li>
          <li><strong>One proposal / opportunity</strong> → <em>Proposals</em></li>
          <li><strong>One A/B test / launch</strong> → <em>Hook A/B Tester</em></li>
          <li><strong>Daily check</strong> → <em>Approvals</em> + <em>Audit</em></li>
        </ul>
        <p className="mt-3 text-emerald-300">Everything runs at <strong>$0/mo</strong>. HF Space, local models, Pollinations — all free, all yours, no per-render charges.</p>
      </>
    ),
  },
];


export function FirstRunWalkthrough() {
  const [open, setOpen] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      const t = setTimeout(() => setOpen(true), 1000);
      return () => clearTimeout(t);
    }
  }, []);

  useEffect(() => {
    window.pe5StartWalkthrough = () => { setStepIdx(0); setOpen(true); };
    return () => { delete window.pe5StartWalkthrough; };
  }, []);

  useEffect(() => {
    const onKey = (e) => {
      if (!open) return;
      if (e.key === "Escape") close();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const close = () => {
    localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    setOpen(false);
  };
  const next = () => {
    if (stepIdx < STEPS.length - 1) {
      const ns = stepIdx + 1;
      setStepIdx(ns);
      if (STEPS[ns].route) navigate(STEPS[ns].route);
    } else close();
  };
  const prev = () => {
    if (stepIdx > 0) {
      const ns = stepIdx - 1;
      setStepIdx(ns);
      if (STEPS[ns].route) navigate(STEPS[ns].route);
    }
  };

  if (!open) return null;
  const step = STEPS[stepIdx];
  const Icon = step.icon;
  const progress = ((stepIdx + 1) / STEPS.length) * 100;
  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center" data-testid="walkthrough-overlay">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-md" onClick={close} />
      <div className="relative max-w-2xl w-[92%] bg-gradient-to-br from-[#0a0414] via-[#13041e] to-[#0a0414] border border-fuchsia-500/30 rounded-2xl shadow-[0_0_60px_rgba(217,70,239,0.25)] p-6 text-white" data-testid="walkthrough-card">
        <button onClick={close} className="absolute top-3 right-3 text-gray-400 hover:text-white" data-testid="walkthrough-close" aria-label="Close walkthrough">
          <X className="w-5 h-5" />
        </button>
        <div className="h-1.5 bg-white/10 rounded-full mb-4 overflow-hidden">
          <div className="h-full bg-gradient-to-r from-fuchsia-500 to-emerald-400 transition-all" style={{ width: `${progress}%` }} />
        </div>
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-fuchsia-500/20 border border-fuchsia-500/40 flex items-center justify-center">
            <Icon className="w-5 h-5 text-fuchsia-300" />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-fuchsia-300">Step {stepIdx + 1} of {STEPS.length}</div>
            <h2 className="text-lg font-bold" data-testid="walkthrough-title">{step.title}</h2>
          </div>
        </div>
        <div className="text-sm leading-relaxed text-gray-200 max-h-[55vh] overflow-y-auto pr-1" data-testid="walkthrough-body">
          {step.body}
        </div>
        <div className="mt-5 flex items-center justify-between">
          <Button variant="outline" size="sm" onClick={prev} disabled={stepIdx === 0}
                  className="border-white/20 bg-white/5 text-white hover:bg-white/10 disabled:opacity-30"
                  data-testid="walkthrough-prev">
            <ChevronLeft className="w-4 h-4 mr-1" /> Back
          </Button>
          <div className="flex items-center gap-1.5">
            {STEPS.map((_, i) => (
              <span key={i} className={`w-1.5 h-1.5 rounded-full transition-all ${i === stepIdx ? "bg-fuchsia-400 w-4" : i < stepIdx ? "bg-emerald-400" : "bg-white/20"}`} />
            ))}
          </div>
          <Button size="sm" onClick={next}
                  className="bg-gradient-to-r from-fuchsia-600 to-emerald-500 text-white hover:from-fuchsia-500 hover:to-emerald-400"
                  data-testid="walkthrough-next">
            {stepIdx === STEPS.length - 1 ? (<>Finish <CheckCircle2 className="w-4 h-4 ml-1" /></>) : (<>Next <ChevronRight className="w-4 h-4 ml-1" /></>)}
          </Button>
        </div>
      </div>
    </div>
  );
}


export function TakeTourButton({ className = "" }) {
  return (
    <button
      onClick={() => window.pe5StartWalkthrough && window.pe5StartWalkthrough()}
      className={`text-xs flex items-center gap-1.5 text-fuchsia-300 hover:text-fuchsia-100 transition-colors ${className}`}
      data-testid="take-tour-btn"
    >
      <Sparkles className="w-3.5 h-3.5" /> Take the tour
    </button>
  );
}
