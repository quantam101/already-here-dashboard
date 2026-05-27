import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { revenueAPI, contentAPI, agentsAPI, ledgerAPI, sovereignAPI, api } from "../lib/api";
import { toast } from "sonner";
import {
  REVENUE_CHART_DAYS, REVENUE_CHART_MIN, REVENUE_CHART_RANGE,
  DAYS_PER_MONTH, HEALTH_BASE, HEALTH_INCREMENT_FACTOR,
  HEALTH_INCREMENT_RANGE, TREND_DOWN_INTERVAL,
} from "../lib/chartConfig";
import MetricsCards from "../components/MetricsCards";
import RevenueChart from "../components/RevenueChart";
import ActivityFeed from "../components/ActivityFeed";
import StreamHealthTable from "../components/StreamHealthTable";
import ProfitMeter from "../components/ProfitMeter";
import RecordEarningsDialog from "../components/RecordEarningsDialog";
import LogPostDialog from "../components/LogPostDialog";
import { Brain, Zap, RefreshCw, Shield, CheckCircle, AlertTriangle } from "lucide-react";

const ACTIVITIES = [
  { id: "act-1", text: "Cash AI decision cycle complete", time: "cash · just now", type: "sovereign" },
  { id: "act-2", text: "LGAC VHLL: 0 resolution — 24 ops validated", time: "vhll · 15 min ago", type: "info" },
  { id: "act-3", text: "A/B title test: variant 3 selected", time: "seo · 19 min ago", type: "info" },
  { id: "act-4", text: "Trend scan: 12 new niches found", time: "trends · 40 min ago", type: "success" },
  { id: "act-5", text: "ContentAgent: article queued for review", time: "content · 1h ago", type: "pending" },
];

function SovereignStatusPanel({ status, onTrigger, isPending, onNav }) {
  const sovereign = status?.sovereign;
  const agents = status?.agents || {};
  const allOk = Object.values(agents).every((a) => a.last_success !== false);

  return (
    <motion.div
      className="sovereign-card cursor-pointer"
      onClick={onNav}
      whileHover={{ scale: 1.005 }}
      transition={{ duration: 0.15 }}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      style={{ border: `1px solid ${allOk ? "rgba(99,102,241,0.25)" : "rgba(239,68,68,0.25)"}` }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="live-dot-indigo" />
          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-widest">Cash AI</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`content-badge ${allOk ? "status-badge-active" : "status-badge-failed"}`}>
            {allOk ? <><CheckCircle className="w-3 h-3 inline mr-1" />All Agents OK</>
                   : <><AlertTriangle className="w-3 h-3 inline mr-1" />Degraded</>}
          </span>
          <button
            onClick={(e) => { e.stopPropagation(); onTrigger(); }}
            disabled={isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-300 rounded-lg transition-all"
            style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.25)" }}
          >
            {isPending ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
            {isPending ? "Running..." : "Trigger"}
          </button>
        </div>
      </div>
      {sovereign?.priority_action ? (
        <p className="text-sm text-gray-300 leading-snug">
          <Brain className="w-3.5 h-3.5 inline mr-1 text-indigo-400" />
          {sovereign.priority_action}
        </p>
      ) : (
        <p className="text-sm text-gray-500">No decision yet — click Trigger to activate governance</p>
      )}
      <div className="flex gap-4 mt-3">
        {Object.entries(agents).map(([id, a]) => (
          <div key={id} className="flex items-center gap-1">
            <span className={`w-1.5 h-1.5 rounded-full inline-block ${a.last_success === false ? "bg-red-500" : a.last_success === true ? "bg-green-500" : "bg-gray-600"}`} />
            <span className="text-xs text-gray-500">{id.replace("-agent", "")}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

export default function Overview() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: revenueStats } = useQuery({ queryKey: ["revenueStats"], queryFn: () => revenueAPI.getStats().then((r) => r.data) });
  const { data: streams = [] } = useQuery({ queryKey: ["revenueStreams"], queryFn: () => revenueAPI.getAll().then((r) => r.data) });
  const { data: contentData = [] } = useQuery({ queryKey: ["content"], queryFn: () => contentAPI.getAll().then((r) => r.data) });
  const { data: agents = [] } = useQuery({ queryKey: ["agents"], queryFn: () => agentsAPI.getAll().then((r) => r.data) });
  const { data: progress } = useQuery({ queryKey: ["ledgerProgress"], queryFn: () => ledgerAPI.progress().then((r) => r.data) });
  const { data: sovereignStatus } = useQuery({
    queryKey: ["sovereignStatus"],
    queryFn: () => sovereignAPI.status().then((r) => r.data),
    refetchInterval: 30_000,
    retry: false,
  });

  const runCycle = useMutation({
    mutationFn: () => api.post("/cycle/run"),
    onSuccess: (res) => {
      const r = res.data;
      toast.success(`Cycle complete — ${r.ideas_created} ideas, ${r.publishing_drafts} drafts`);
      qc.invalidateQueries({ queryKey: ["publishing"] });
      qc.invalidateQueries({ queryKey: ["content"] });
    },
    onError: (err) => toast.error(`Cycle failed: ${err?.response?.data?.detail || err.message}`),
  });

  const triggerSovereign = useMutation({
    mutationFn: () => sovereignAPI.trigger(),
    onSuccess: (res) => {
      const d = res.data;
      if (d.status === "skipped") toast.info(`Cash skipped: ${d.skip_reason}`);
      else toast.success(`Cash dispatched ${d.agents_dispatched?.length || 0} agents`);
      qc.invalidateQueries({ queryKey: ["sovereignStatus"] });
    },
    onError: (e) => toast.error(`Cash failed: ${e?.response?.data?.detail || e.message}`),
  });

  const revenueChartData = useMemo(() =>
    Array.from({ length: REVENUE_CHART_DAYS }, (_, i) => ({
      day: `Day ${i + 1}`,
      revenue: Math.floor(Math.random() * REVENUE_CHART_RANGE) + REVENUE_CHART_MIN,
    })), []);

  const metrics = useMemo(() => {
    const mrr = revenueStats?.total_monthly_actual || 0;
    const mrrGrowth = revenueStats?.achievement_percentage || 0;
    const activeStreams = streams.filter((s) => s.status === "active").length;
    const totalStreams = streams.length;
    const contentToday = contentData.filter((c) => new Date(c.created_at).toDateString() === new Date().toDateString()).length;
    const totalAgentRuns = agents.reduce((sum, a) => sum + (a.run_count || 0), 0);
    return { mrr, mrrGrowth, activeStreams, totalStreams, contentToday, totalAgentRuns };
  }, [revenueStats, streams, contentData, agents]);

  const enrichedStreams = useMemo(() => streams.map((s, i) => ({
    ...s,
    health: HEALTH_BASE + ((i * HEALTH_INCREMENT_FACTOR) % HEALTH_INCREMENT_RANGE),
    trend: i % TREND_DOWN_INTERVAL !== 0,
  })), [streams]);

  const todayProfit = useMemo(() => streams.reduce((sum, s) => sum + (s.monthly_actual || 0) / DAYS_PER_MONTH, 0), [streams]);

  return (
    <div data-testid="overview-page" className="p-6 space-y-6">
      {/* Header */}
      <motion.div
        className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4"
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <div>
          <h1 className="text-3xl font-bold text-white mb-0.5" style={{ fontFamily: "Space Grotesk" }}>
            Command Center
          </h1>
          <p className="text-gray-400 text-sm">engine running · LGAC VHLL · Cash governed · 24/7</p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <LogPostDialog />
          <RecordEarningsDialog />
          <button
            data-testid="run-cycle-btn"
            onClick={() => runCycle.mutate()}
            disabled={runCycle.isPending}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg transition-colors text-sm font-medium"
          >
            {runCycle.isPending ? "Running..." : "Run Cycle"}
          </button>
          <button
            onClick={() => navigate("/sovereign")}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-indigo-300 rounded-lg transition-colors"
            style={{ background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.22)" }}
          >
            <Brain className="w-4 h-4" /> Cash AI
          </button>
          <button data-testid="pause-all-btn" className="px-4 py-2 bg-transparent border border-gray-700 text-gray-300 rounded-lg hover:bg-gray-800 transition-colors text-sm">
            Pause All
          </button>
        </div>
      </motion.div>

      {/* Sovereign AI status panel */}
      <SovereignStatusPanel
        status={sovereignStatus}
        onTrigger={() => triggerSovereign.mutate()}
        isPending={triggerSovereign.isPending}
        onNav={() => navigate("/sovereign")}
      />

      {/* Profit meter */}
      <ProfitMeter progress={progress} />

      {/* Top metrics */}
      <MetricsCards {...metrics} />

      {/* Revenue chart + activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RevenueChart data={revenueChartData} />
        </div>
        <ActivityFeed activities={ACTIVITIES} />
      </div>

      {/* Stream health */}
      <StreamHealthTable streams={enrichedStreams} />

      {/* Today's Profit Badge */}
      <div className="profit-badge" data-testid="profit-badge">
        <div className="text-white/70 text-xs font-semibold mb-1 uppercase tracking-wider">Today&apos;s Profit</div>
        <div className="text-3xl font-bold text-white">${todayProfit.toFixed(2)}</div>
        <div className="text-white/55 text-xs mt-0.5">+12.3% vs avg · {metrics.activeStreams} streams</div>
      </div>
    </div>
  );
}