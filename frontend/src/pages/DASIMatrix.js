import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCopy,
  Cpu,
  ExternalLink,
  GitBranch,
  Play,
  RefreshCw,
  Shield,
  ShieldCheck,
  Trash2,
  Zap,
} from "lucide-react";
import { dasiAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

// ─── Constants ─────────────────────────────────────────────────────────────

const MAX_DIRECTIVE_CHARS = 8192;

const STAGE_META = [
  {
    step: 1,
    id: "orchestrator_router",
    label: "Orchestrator Router",
    role: "Strategic Execution Path Planner",
    register: "global_trajectory",
    icon: GitBranch,
    color: "text-indigo-400",
    border: "border-indigo-500/30",
    bg: "bg-indigo-500/8",
    glow: "shadow-indigo-500/20",
  },
  {
    step: 2,
    id: "context_distiller",
    label: "Context Distiller",
    role: "High-Density Semantic Condenser",
    register: "compressed_payload",
    icon: Cpu,
    color: "text-sky-400",
    border: "border-sky-500/30",
    bg: "bg-sky-500/8",
    glow: "shadow-sky-500/20",
  },
  {
    step: 3,
    id: "execution_unit",
    label: "Execution Unit",
    role: "Production-Grade Blueprint Architect",
    register: "compiled_architecture",
    icon: Zap,
    color: "text-amber-400",
    border: "border-amber-500/30",
    bg: "bg-amber-500/8",
    glow: "shadow-amber-500/20",
  },
  {
    step: 4,
    id: "adversarial_critic",
    label: "Adversarial Critic",
    role: "Automated Policy Compliance Inspector",
    register: "validated_enterprise_output",
    icon: ShieldCheck,
    color: "text-emerald-400",
    border: "border-emerald-500/30",
    bg: "bg-emerald-500/8",
    glow: "shadow-emerald-500/20",
  },
];

const JOB_STATUS_META = {
  pending: {
    label: "QUEUED",
    color: "text-slate-400",
    bg: "bg-slate-500/15 border-slate-500/30",
    dot: "bg-slate-400",
    pulse: false,
  },
  PROCESSING: {
    label: "PROCESSING",
    color: "text-indigo-300",
    bg: "bg-indigo-500/15 border-indigo-500/30",
    dot: "bg-indigo-400",
    pulse: true,
  },
  SUCCESS_STABLE: {
    label: "SUCCESS",
    color: "text-emerald-300",
    bg: "bg-emerald-500/15 border-emerald-500/30",
    dot: "bg-emerald-400",
    pulse: false,
  },
  FAILED: {
    label: "FAILED",
    color: "text-rose-300",
    bg: "bg-rose-500/15 border-rose-500/30",
    dot: "bg-rose-400",
    pulse: false,
  },
  HALTED_ON_SECURITY_VIOLATION: {
    label: "HALTED",
    color: "text-orange-300",
    bg: "bg-orange-500/15 border-orange-500/30",
    dot: "bg-orange-400",
    pulse: false,
  },
};

// ─── Helpers ───────────────────────────────────────────────────────────────

function isTerminal(status) {
  return ["SUCCESS_STABLE", "FAILED", "HALTED_ON_SECURITY_VIOLATION"].includes(status);
}

function elapsed(created_at) {
  if (!created_at) return null;
  const ms = Date.now() - new Date(created_at).getTime();
  if (ms < 60000) return `${Math.round(ms / 1000)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

// ─── Sub-components ────────────────────────────────────────────────────────

function StatusPill({ status }) {
  const meta = JOB_STATUS_META[status] || {
    label: status || "UNKNOWN",
    color: "text-slate-400",
    bg: "bg-slate-500/15 border-slate-500/30",
    dot: "bg-slate-400",
    pulse: false,
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-xs font-bold tracking-wider ${meta.bg} ${meta.color}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${meta.dot} ${meta.pulse ? "animate-pulse" : ""}`} />
      {meta.label}
    </span>
  );
}

function StageCard({ stage, currentStep, matrixContext, isActive }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = stage.icon;
  const isDone = currentStep >= stage.step;
  const isRunning = currentStep === stage.step - 1 && isActive;
  const content = matrixContext?.[stage.register];

  return (
    <div
      className={`rounded-xl border transition-all duration-300 ${stage.border} ${stage.bg} ${
        isRunning ? `shadow-lg ${stage.glow}` : ""
      } ${isDone ? "opacity-100" : "opacity-50"}`}
    >
      <div className="flex items-center gap-3 p-4">
        <div
          className={`w-9 h-9 rounded-lg flex items-center justify-center border ${stage.border} ${stage.bg}`}
        >
          {isDone ? (
            <CheckCircle2 className={`w-4 h-4 ${stage.color}`} />
          ) : isRunning ? (
            <Icon className={`w-4 h-4 ${stage.color} animate-pulse`} />
          ) : (
            <Icon className={`w-4 h-4 text-slate-600`} />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 text-xs font-mono">STEP {stage.step}</span>
            <span className={`text-sm font-semibold ${isDone || isRunning ? stage.color : "text-slate-600"}`}>
              {stage.label}
            </span>
            {isRunning && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold tracking-wider animate-pulse">
                ACTIVE
              </span>
            )}
          </div>
          <p className={`text-xs mt-0.5 ${isDone || isRunning ? "text-slate-400" : "text-slate-600"}`}>
            {stage.role}
          </p>
        </div>

        {content && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
      </div>

      {expanded && content && (
        <div className="px-4 pb-4">
          <div
            className="rounded-lg p-3 border border-white/5 font-mono text-xs text-slate-300 leading-relaxed overflow-auto max-h-64 whitespace-pre-wrap"
            style={{ background: "rgba(0,0,0,0.4)" }}
          >
            {content}
          </div>
        </div>
      )}
    </div>
  );
}

function JobCard({ job, onDelete }) {
  const [expanded, setExpanded] = useState(false);
  const qc = useQueryClient();
  const terminal = isTerminal(job.status);

  const { data: liveJob } = useQuery({
    queryKey: ["dasiJob", job.job_id],
    queryFn: () => dasiAPI.job(job.job_id).then((r) => r.data),
    refetchInterval: !terminal ? 2500 : false,
    initialData: job,
  });

  const data = liveJob || job;
  const matCtx = data.matrix_context || {};
  const isActive = data.status === "PROCESSING";

  const copyResult = useCallback(() => {
    const result = data.result || matCtx.validated_enterprise_output || "";
    if (!result) { toast.error("No result to copy yet"); return; }
    navigator.clipboard.writeText(result).then(() => toast.success("Result copied to clipboard"));
  }, [data.result, matCtx.validated_enterprise_output]);

  const openResult = useCallback(() => {
    window.open(dasiAPI.resultUrl(data.job_id), "_blank", "noopener");
  }, [data.job_id]);

  return (
    <div
      className="rounded-xl border transition-all"
      style={{ background: "rgba(255,255,255,0.02)", borderColor: "rgba(255,255,255,0.07)" }}
    >
      {/* Header row */}
      <div className="flex items-center gap-3 p-4">
        <StatusPill status={data.status} />

        <div className="flex-1 min-w-0">
          <p className="text-xs font-mono text-slate-400 truncate">{data.job_id}</p>
          <p className="text-xs text-slate-500 truncate mt-0.5">
            {data.directive
              ? data.directive.slice(0, 80) + (data.directive.length > 80 ? "…" : "")
              : "(no directive)"}
          </p>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Step indicator */}
          <span className="text-xs font-mono text-slate-500 mr-1">
            {data.current_step}/{4}
          </span>

          {data.status === "SUCCESS_STABLE" && (
            <>
              <button
                title="Copy result"
                onClick={copyResult}
                className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-sky-300 transition-colors"
              >
                <ClipboardCopy className="w-3.5 h-3.5" />
              </button>
              <button
                title="Open raw result"
                onClick={openResult}
                className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-emerald-300 transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </>
          )}

          <button
            onClick={() => setExpanded((v) => !v)}
            className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          <button
            title="Delete job"
            onClick={() => onDelete(data.job_id)}
            className="p-1.5 rounded hover:bg-rose-500/10 text-slate-600 hover:text-rose-400 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Elapsed / error */}
      {data.created_at && (
        <div className="px-4 pb-2 flex items-center gap-3">
          <span className="text-xs text-slate-600">
            {elapsed(data.created_at)} elapsed
          </span>
          {data.error && (
            <span className="text-xs text-rose-400 truncate flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 flex-shrink-0" />
              {data.error.slice(0, 100)}
            </span>
          )}
        </div>
      )}

      {/* Stage pipeline expansion */}
      {expanded && (
        <div className="px-4 pb-4 space-y-2">
          {STAGE_META.map((stage) => (
            <StageCard
              key={stage.id}
              stage={stage}
              currentStep={data.current_step}
              matrixContext={matCtx}
              isActive={isActive}
            />
          ))}

          {/* Telemetry log */}
          {data.telemetry && data.telemetry.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Telemetry
              </p>
              <div
                className="rounded-lg p-3 border border-white/5 space-y-1"
                style={{ background: "rgba(0,0,0,0.3)" }}
              >
                {data.telemetry.map((entry, i) => (
                  <p key={i} className="text-xs font-mono text-slate-400">
                    {entry}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function HealthPanel({ health }) {
  if (!health) return null;
  const items = [
    { label: "Manifest", ok: health.manifest_loaded, value: health.version },
    { label: "HF Token", ok: health.hf_token_set, value: health.hf_token_set ? "Set" : "Missing" },
    { label: "Primary LLM", ok: true, value: health.primary_llm?.split("/").pop() },
    { label: "Fallback LLM", ok: true, value: health.fallback_llm?.split("/").pop() },
    { label: "Agents", ok: health.agent_count === 4, value: `${health.agent_count} loaded` },
    { label: "Policies", ok: health.policy_count > 0, value: `${health.policy_count} active` },
  ];
  return (
    <div
      className="rounded-xl border p-4 grid grid-cols-2 sm:grid-cols-3 gap-3"
      style={{ background: "rgba(255,255,255,0.02)", borderColor: "rgba(255,255,255,0.07)" }}
    >
      {items.map(({ label, ok, value }) => (
        <div key={label} className="flex flex-col gap-0.5">
          <span className="text-xs text-slate-500 uppercase tracking-wider">{label}</span>
          <span className={`text-sm font-semibold ${ok ? "text-emerald-400" : "text-rose-400"}`}>
            {value || "—"}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────

export default function DASIMatrix() {
  const [directive, setDirective] = useState("");
  const qc = useQueryClient();

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["dasiHealth"],
    queryFn: () => dasiAPI.health().then((r) => r.data),
    refetchInterval: 30_000,
    retry: false,
  });

  const { data: jobs = [], isLoading: jobsLoading, refetch: refetchJobs } = useQuery({
    queryKey: ["dasiTelemetry"],
    queryFn: () => dasiAPI.telemetry(50).then((r) => r.data),
    refetchInterval: 5000,
  });

  const executeMutation = useMutation({
    mutationFn: (dir) => dasiAPI.execute(dir),
    onSuccess: (res) => {
      const { job_id } = res.data;
      toast.success(`Swarm job queued — ID: ${job_id}`);
      setDirective("");
      qc.invalidateQueries({ queryKey: ["dasiTelemetry"] });
    },
    onError: (err) => {
      const detail = err?.response?.data?.detail || err.message || "Unknown error";
      toast.error(`Execute failed: ${detail}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => dasiAPI.deleteJob(id),
    onSuccess: () => {
      toast.success("Job deleted");
      qc.invalidateQueries({ queryKey: ["dasiTelemetry"] });
    },
    onError: () => toast.error("Delete failed"),
  });

  const handleExecute = useCallback(() => {
    const trimmed = directive.trim();
    if (!trimmed) { toast.error("Directive cannot be empty"); return; }
    if (trimmed.length > MAX_DIRECTIVE_CHARS) {
      toast.error(`Directive exceeds ${MAX_DIRECTIVE_CHARS.toLocaleString()} character limit`);
      return;
    }
    if (!health?.ready) {
      toast.error("D-ASI engine not ready — check health panel above");
      return;
    }
    executeMutation.mutate(trimmed);
  }, [directive, health, executeMutation]);

  const charsLeft = MAX_DIRECTIVE_CHARS - directive.length;
  const isOverLimit = charsLeft < 0;

  const runningCount = jobs.filter((j) => j.status === "PROCESSING").length;
  const successCount = jobs.filter((j) => j.status === "SUCCESS_STABLE").length;

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8" style={{ background: "#070C19" }}>
      <div className="max-w-4xl mx-auto space-y-6">

        {/* ── Header ── */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{
                  background: "linear-gradient(135deg, #6366f1, #4f46e5)",
                  boxShadow: "0 0 20px rgba(99,102,241,0.35)",
                }}
              >
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1
                  className="text-xl font-bold text-white leading-tight"
                  style={{ fontFamily: "Space Grotesk" }}
                >
                  D-ASI Matrix
                </h1>
                <p className="text-xs text-slate-500 font-mono">
                  Declarative Autonomous Swarm Intelligence · v4.0.0-ENTERPRISE
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Running badge */}
            {runningCount > 0 && (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-500/15 border border-indigo-500/30 text-indigo-300">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
                {runningCount} running
              </span>
            )}
            <button
              onClick={() => { refetchJobs(); qc.invalidateQueries({ queryKey: ["dasiHealth"] }); }}
              className="p-2 rounded-lg hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${jobsLoading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* ── Status strip ── */}
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5" />
            {jobs.length} total jobs
          </span>
          <span className="flex items-center gap-1.5 text-emerald-500">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {successCount} succeeded
          </span>
          {health && (
            <span
              className={`flex items-center gap-1.5 ${health.ready ? "text-emerald-500" : "text-rose-400"}`}
            >
              <Shield className="w-3.5 h-3.5" />
              {health.ready ? "Engine ready" : "Engine degraded"}
            </span>
          )}
        </div>

        {/* ── Health panel ── */}
        {healthLoading ? (
          <div
            className="rounded-xl border p-4 animate-pulse"
            style={{ background: "rgba(255,255,255,0.02)", borderColor: "rgba(255,255,255,0.07)" }}
          >
            <div className="h-4 bg-white/5 rounded w-1/3 mb-2" />
            <div className="h-3 bg-white/5 rounded w-1/2" />
          </div>
        ) : (
          <HealthPanel health={health} />
        )}

        {/* ── Execute form ── */}
        <div
          className="rounded-xl border p-5 space-y-4"
          style={{ background: "rgba(255,255,255,0.025)", borderColor: "rgba(99,102,241,0.25)" }}
        >
          <div className="flex items-center gap-2 mb-1">
            <Zap className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-semibold text-white">Execute Directive</h2>
          </div>

          <div className="relative">
            <textarea
              value={directive}
              onChange={(e) => setDirective(e.target.value)}
              placeholder={
                "Describe the artifact you need the D-ASI swarm to generate.\n\n" +
                "Examples:\n" +
                "• Generate a production-ready FastAPI CRUD router for a 'products' collection with full Pydantic v2 models.\n" +
                "• Write a complete GitHub Actions CI/CD workflow that builds a Docker image and pushes to GHCR.\n" +
                "• Create a Terraform module for provisioning an OCI Always Free compute instance with Docker."
              }
              rows={8}
              className={`w-full rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 resize-none focus:outline-none focus:ring-1 ${
                isOverLimit ? "focus:ring-rose-500 ring-1 ring-rose-500" : "focus:ring-indigo-500"
              }`}
              style={{
                background: "rgba(0,0,0,0.4)",
                border: "1px solid rgba(99,102,241,0.2)",
                fontFamily: directive.length > 0 ? "inherit" : "inherit",
              }}
            />
            <span
              className={`absolute bottom-3 right-3 text-xs font-mono ${
                isOverLimit ? "text-rose-400" : charsLeft < 500 ? "text-amber-400" : "text-slate-600"
              }`}
            >
              {charsLeft.toLocaleString()}
            </span>
          </div>

          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-slate-600">
              4-stage swarm: orchestrate → distill → execute → validate
            </p>
            <Button
              onClick={handleExecute}
              disabled={
                executeMutation.isPending ||
                !directive.trim() ||
                isOverLimit ||
                !health?.ready
              }
              className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold text-white transition-all"
              style={{
                background: "linear-gradient(135deg, #6366f1, #4f46e5)",
                boxShadow: "0 0 16px rgba(99,102,241,0.3)",
                opacity: executeMutation.isPending || !directive.trim() || isOverLimit || !health?.ready ? 0.5 : 1,
              }}
            >
              {executeMutation.isPending ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {executeMutation.isPending ? "Queuing…" : "Execute Swarm"}
            </Button>
          </div>

          {/* Config notes from health */}
          {health?.notes && health.notes.length > 0 && !health.ready && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                {health.notes.map((n, i) => (
                  <p key={i} className="text-xs text-amber-300">{n}</p>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Job list ── */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-400" />
              Swarm Telemetry
              <span className="text-xs font-normal text-slate-600">({jobs.length} jobs)</span>
            </h2>
          </div>

          {jobsLoading && jobs.length === 0 ? (
            <div className="space-y-3">
              {[1, 2, 3].map((n) => (
                <div
                  key={n}
                  className="rounded-xl border animate-pulse p-4 h-16"
                  style={{ background: "rgba(255,255,255,0.02)", borderColor: "rgba(255,255,255,0.07)" }}
                />
              ))}
            </div>
          ) : jobs.length === 0 ? (
            <div
              className="rounded-xl border p-10 text-center"
              style={{ background: "rgba(255,255,255,0.02)", borderColor: "rgba(255,255,255,0.07)" }}
            >
              <Bot className="w-10 h-10 text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">No swarm jobs yet</p>
              <p className="text-slate-600 text-xs mt-1">
                Enter a directive above and click Execute Swarm to start the pipeline.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <JobCard
                  key={job.job_id}
                  job={job}
                  onDelete={(id) => deleteMutation.mutate(id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Architecture note ── */}
        <div
          className="rounded-xl border p-4 mt-2"
          style={{ background: "rgba(255,255,255,0.015)", borderColor: "rgba(255,255,255,0.06)" }}
        >
          <p className="text-xs text-slate-600 font-mono leading-relaxed">
            <span className="text-indigo-500">orchestrator_router</span>
            {" → "}
            <span className="text-sky-500">context_distiller</span>
            {" → "}
            <span className="text-amber-500">execution_unit</span>
            {" → "}
            <span className="text-emerald-500">adversarial_critic</span>
            {" · "}
            <span className="text-slate-500">
              asyncio.PriorityQueue · exponential backoff + jitter · per-job DB isolation ·
              append-only audit log · zero-placeholder policy enforcement
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
