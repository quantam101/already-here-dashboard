import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { sovereignAPI } from "../lib/api";
import { toast } from "sonner";
import {
  Brain, Zap, Shield, Radar, PenLine, DollarSign,
  CheckCircle, XCircle, AlertTriangle, Clock, RefreshCw,
  Activity, Cpu, TrendingUp, Terminal,
} from "lucide-react";

// ── Agent metadata ──────────────────────────────────────────────────────────
const AGENT_META = {
  "guard-agent":   { icon: Shield,   color: "#22c55e", label: "Infrastructure Guardian", schedule: "Every 15 min", tokens: 0 },
  "scout-agent":   { icon: Radar,    color: "#3b82f6", label: "Trend Scout",             schedule: "Every hour",   tokens: 0 },
  "content-agent": { icon: PenLine,  color: "#a855f7", label: "Content Generator",       schedule: "Every 6 hrs",  tokens: 8000 },
  "revenue-agent": { icon: DollarSign, color: "#f59e0b", label: "Revenue Tracker",      schedule: "Every 30 min", tokens: 200 },
};

function RiskPill({ level }) {
  const cfg = {
    low:    { cls: "status-badge-active",   label: "LOW RISK" },
    medium: { cls: "status-badge-degraded", label: "MED RISK" },
    high:   { cls: "status-badge-failed",   label: "HIGH RISK" },
  };
  const { cls, label } = cfg[level] || cfg.low;
  return <span className={`content-badge ${cls}`}>{label}</span>;
}

function AgentStatusDot({ success }) {
  if (success === null || success === undefined)
    return <span className="w-2 h-2 rounded-full bg-gray-600 inline-block" />;
  return success
    ? <span className="live-dot" style={{ width: 8, height: 8 }} />
    : <span className="w-2 h-2 rounded-full bg-red-500 inline-block" style={{ boxShadow: "0 0 6px rgba(239,68,68,0.5)" }} />;
}

function AgentCard({ agentId, agentStatus, index }) {
  const meta = AGENT_META[agentId] || { icon: Cpu, color: "#9ca3af", label: agentId, schedule: "—", tokens: 0 };
  const Icon = meta.icon;
  const status = agentStatus?.[agentId];
  const isHealthy = status?.last_success !== false;
  const cardClass = `agent-card ${isHealthy ? "agent-healthy" : "agent-error"} slide-in-up`;

  return (
    <motion.div
      className={cardClass}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07, duration: 0.4 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: `${meta.color}18`, border: `1px solid ${meta.color}30` }}>
            <Icon className="w-4 h-4" style={{ color: meta.color }} />
          </div>
          <div>
            <p className="text-xs font-semibold text-white leading-tight">{meta.label}</p>
            <p className="text-xs text-gray-500">{agentId}</p>
          </div>
        </div>
        <AgentStatusDot success={status?.last_success} />
      </div>

      {/* Schedule + token budget */}
      <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
        <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {meta.schedule}</span>
        <span className="text-purple-400">{meta.tokens === 0 ? "0 tokens" : `≤${meta.tokens.toLocaleString()} tok`}</span>
      </div>

      {/* Last run info */}
      {status?.last_run && (
        <div className="text-xs text-gray-400 mb-2 flex items-center gap-1">
          <Activity className="w-3 h-3" />
          Last: {new Date(status.last_run).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          {status.duration_ms && <span className="ml-1 text-gray-600">· {status.duration_ms}ms</span>}
        </div>
      )}

      {/* Error if any */}
      {status?.last_error && (
        <div className="text-xs text-red-400 truncate bg-red-500/10 rounded px-2 py-1 mt-1 border border-red-500/20">
          {status.last_error}
        </div>
      )}

      {/* Token budget bar */}
      {meta.tokens > 0 && (
        <div className="mt-2">
          <div className="cb-bar">
            <div className="cb-fill-ok" style={{ width: isHealthy ? "100%" : "0%" }} />
          </div>
        </div>
      )}
    </motion.div>
  );
}

function DecisionCard({ decision, index }) {
  if (!decision) return null;
  const riskColor = decision.risk_level === "high" ? "#ef4444" : decision.risk_level === "medium" ? "#f59e0b" : "#22c55e";
  return (
    <motion.div
      className="enterprise-card mb-3"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04, duration: 0.35 }}
      style={{ borderLeft: `3px solid ${riskColor}` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white mb-1 leading-snug">{decision.priority_action}</p>
          <p className="text-xs text-gray-400 mb-2">{decision.reasoning}</p>
          <div className="flex flex-wrap gap-1.5">
            {(decision.agents_to_run || []).map((a) => {
              const m = AGENT_META[a];
              return (
                <span key={a} className="content-badge"
                  style={{ background: `${m?.color || "#6366f1"}18`, color: m?.color || "#a5b4fc", border: `1px solid ${m?.color || "#6366f1"}30` }}>
                  {a.replace("-agent", "")}
                </span>
              );
            })}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <RiskPill level={decision.risk_level} />
          <span className="text-xs text-gray-600">
            {decision.made_at ? new Date(decision.made_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}
          </span>
        </div>
      </div>
    </motion.div>
  );
}

export default function Sovereign() {
  const qc = useQueryClient();

  const { data: statusData, isLoading: statusLoading } = useQuery({
    queryKey: ["sovereignStatus"],
    queryFn: () => sovereignAPI.status().then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: historyData } = useQuery({
    queryKey: ["sovereignHistory"],
    queryFn: () => sovereignAPI.history(15).then((r) => r.data),
    refetchInterval: 60_000,
  });

  const trigger = useMutation({
    mutationFn: () => sovereignAPI.trigger(),
    onSuccess: (res) => {
      const d = res.data;
      if (d.status === "skipped") {
        toast.info(`Cash skipped: ${d.skip_reason}`);
      } else {
        toast.success(`Cash cycle complete — ${d.agents_dispatched?.length || 0} agents dispatched`);
      }
      qc.invalidateQueries({ queryKey: ["sovereignStatus"] });
      qc.invalidateQueries({ queryKey: ["sovereignHistory"] });
    },
    onError: (e) => toast.error(`Trigger failed: ${e?.response?.data?.detail || e.message}`),
  });

  const clearCache = useMutation({
    mutationFn: () => sovereignAPI.clearCache(),
    onSuccess: () => toast.success("Cash AI cache cleared — next cycle will call AI fresh"),
    onError: () => toast.error("Cache clear failed"),
  });

  const sovereign = statusData?.sovereign;
  const agentStatus = statusData?.agents || {};
  const decisions = historyData?.decisions || [];
  const agentIds = Object.keys(AGENT_META);

  const allHealthy = agentIds.every((id) => agentStatus[id]?.last_success !== false);

  return (
    <div className="p-6 space-y-6" data-testid="sovereign-page">
      {/* ── Header ── */}
      <motion.div
        className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)" }}>
              <Brain className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white" style={{ fontFamily: "Space Grotesk" }}>
                Cash AI
              </h1>
              <p className="text-gray-400 text-sm">Governing intelligence · dispatch authority · immutable audit</p>
            </div>
          </div>
        </div>
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={() => clearCache.mutate()}
            disabled={clearCache.isPending}
            className="px-4 py-2 border border-indigo-500/30 text-indigo-400 rounded-lg text-sm hover:bg-indigo-500/10 transition-colors"
          >
            Clear AI Cache
          </button>
          <button
            onClick={() => trigger.mutate()}
            disabled={trigger.isPending}
            className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold text-white transition-all"
            style={{
              background: trigger.isPending
                ? "rgba(99,102,241,0.4)"
                : "linear-gradient(135deg, #6366f1, #4f46e5)",
              boxShadow: trigger.isPending ? "none" : "0 0 20px rgba(99,102,241,0.35)",
            }}
          >
            {trigger.isPending
              ? <><RefreshCw className="w-4 h-4 animate-spin" /> Running...</>
              : <><Zap className="w-4 h-4" /> Trigger Cycle</>}
          </button>
        </div>
      </motion.div>

      {/* ── Current Decision Banner ── */}
      <motion.div
        className="sovereign-card neural-bg"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-3">
              <span className="live-dot-indigo" />
              <span className="text-xs font-semibold text-indigo-400 uppercase tracking-widest">Last Cash Decision</span>
              {sovereign?.made_at && (
                <span className="text-xs text-gray-600">
                  · {new Date(sovereign.made_at).toLocaleString()}
                </span>
              )}
            </div>
            {statusLoading ? (
              <div className="h-6 w-72 rounded shimmer-bg" />
            ) : sovereign && sovereign.priority_action ? (
              <>
                <p className="text-xl font-bold text-white mb-2" style={{ fontFamily: "Space Grotesk" }}>
                  {sovereign.priority_action}
                </p>
                <p className="text-sm text-gray-400 mb-4">{sovereign.reasoning}</p>
                <div className="flex flex-wrap gap-2">
                  {(sovereign.agents_to_run || []).map((a) => {
                    const m = AGENT_META[a];
                    return (
                      <span key={a} className="content-badge text-xs px-3 py-1"
                        style={{ background: `${m?.color || "#6366f1"}15`, color: m?.color || "#a5b4fc", border: `1px solid ${m?.color || "#6366f1"}28` }}>
                        {m?.label || a}
                      </span>
                    );
                  })}
                </div>
              </>
            ) : (
              <p className="text-gray-500 text-sm">No decisions recorded yet — trigger a Cash cycle to begin.</p>
            )}
          </div>
          <div className="flex-shrink-0 flex flex-col items-end gap-2">
            {sovereign?.risk_level && <RiskPill level={sovereign.risk_level} />}
            <span className={`content-badge ${allHealthy ? "status-badge-active" : "status-badge-degraded"}`}>
              {allHealthy ? <><CheckCircle className="w-3 h-3 inline mr-1" />ALL OK</> : <><AlertTriangle className="w-3 h-3 inline mr-1" />DEGRADED</>}
            </span>
          </div>
        </div>
      </motion.div>

      {/* ── Agent Fleet Grid ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-400" /> Agent Fleet
          </h2>
          <span className="text-xs text-gray-500">{agentIds.length} registered · auto-refresh 30s</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {agentIds.map((id, i) => (
            <AgentCard key={id} agentId={id} agentStatus={agentStatus} index={i} />
          ))}
        </div>
      </div>

      {/* ── Decision History ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Terminal className="w-4 h-4 text-indigo-400" /> Decision Audit Trail
          </h2>
          <span className="text-xs text-gray-500">{decisions.length} decisions recorded</span>
        </div>
        {decisions.length === 0 ? (
          <div className="enterprise-card text-center py-10 text-gray-500 text-sm">
            No decisions yet. Trigger a Cash cycle to begin governance.
          </div>
        ) : (
          <div className="max-h-[500px] overflow-y-auto pr-1 space-y-2">
            <AnimatePresence>
              {decisions.map((d, i) => <DecisionCard key={d.decision_id || i} decision={d} index={i} />)}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}