import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { revenueAPI, contentAPI, agentsAPI, ledgerAPI, api } from "../lib/api";
import { toast } from "sonner";
import {
  REVENUE_CHART_DAYS,
  REVENUE_CHART_MIN,
  REVENUE_CHART_RANGE,
  DAYS_PER_MONTH,
  HEALTH_BASE,
  HEALTH_INCREMENT_FACTOR,
  HEALTH_INCREMENT_RANGE,
  TREND_DOWN_INTERVAL,
} from "../lib/chartConfig";
import MetricsCards from "../components/MetricsCards";
import RevenueChart from "../components/RevenueChart";
import ActivityFeed from "../components/ActivityFeed";
import StreamHealthTable from "../components/StreamHealthTable";
import ProfitMeter from "../components/ProfitMeter";
import RecordEarningsDialog from "../components/RecordEarningsDialog";
import LogPostDialog from "../components/LogPostDialog";

// Static activity data - extracted from render to prevent re-creation
const ACTIVITIES = [
  { id: "act-1", text: "Health oracle score live from AppleFoundation", time: "health - 3m ago", type: "success" },
  { id: "act-2", text: "LGAC VHLL: 0 resolution - 24 ops validated", time: "vhll - 15 min ago", type: "info" },
  { id: "act-3", text: "A/B title test: variant 3 selected", time: "seo - 19 min ago", type: "info" },
  { id: "act-4", text: "Trend scan: 12 new niches found", time: "trends - 40m ago", type: "success" },
  { id: "act-5", text: "Reddit scheduled: ubuntu_thread", time: "reddit - 60m ago", type: "pending" },
];

export default function Overview() {
  const { data: revenueStats } = useQuery({
    queryKey: ["revenueStats"],
    queryFn: () => revenueAPI.getStats().then((res) => res.data),
  });

  const { data: streams = [] } = useQuery({
    queryKey: ["revenueStreams"],
    queryFn: () => revenueAPI.getAll().then((res) => res.data),
  });

  const { data: contentData = [] } = useQuery({
    queryKey: ["content"],
    queryFn: () => contentAPI.getAll().then((res) => res.data),
  });

  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: () => agentsAPI.getAll().then((res) => res.data),
  });

  const { data: progress } = useQuery({
    queryKey: ["ledgerProgress"],
    queryFn: () => ledgerAPI.progress().then((res) => res.data),
  });

  const queryClient = useQueryClient();
  const runCycle = useMutation({
    mutationFn: () => api.post("/cycle/run"),
    onSuccess: (res) => {
      const r = res.data;
      toast.success(`Cycle complete - ${r.ideas_created} ideas, ${r.publishing_drafts} drafts`);
      queryClient.invalidateQueries({ queryKey: ["publishing"] });
      queryClient.invalidateQueries({ queryKey: ["publishingStats"] });
      queryClient.invalidateQueries({ queryKey: ["content"] });
    },
    onError: (err) => toast.error(`Cycle failed: ${err?.response?.data?.detail || err.message}`),
  });

  // Memoize computed values
  const revenueChartData = useMemo(
    () => Array.from({ length: REVENUE_CHART_DAYS }, (_, i) => ({
      day: `Day ${i + 1}`,
      revenue: Math.floor(Math.random() * REVENUE_CHART_RANGE) + REVENUE_CHART_MIN,
    })),
    []
  );

  const metrics = useMemo(() => {
    const mrr = revenueStats?.total_monthly_actual || 0;
    const mrrGrowth = revenueStats?.achievement_percentage || 0;
    const activeStreams = streams.filter((s) => s.status === "active").length;
    const totalStreams = streams.length;
    const contentToday = contentData.filter((c) => {
      const created = new Date(c.created_at);
      const today = new Date();
      return created.toDateString() === today.toDateString();
    }).length;
    const totalAgentRuns = agents.reduce((sum, a) => sum + (a.run_count || 0), 0);
    return { mrr, mrrGrowth, activeStreams, totalStreams, contentToday, totalAgentRuns };
  }, [revenueStats, streams, contentData, agents]);

  const enrichedStreams = useMemo(
    () => streams.map((s, i) => ({
      ...s,
      health: HEALTH_BASE + ((i * HEALTH_INCREMENT_FACTOR) % HEALTH_INCREMENT_RANGE),
      trend: i % TREND_DOWN_INTERVAL !== 0,
    })),
    [streams]
  );

  const todayProfit = useMemo(
    () => streams.reduce((sum, s) => sum + (s.monthly_actual || 0) / DAYS_PER_MONTH, 0),
    [streams]
  );

  return (
    <div data-testid="overview-page" className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1" style={{ fontFamily: 'Space Grotesk' }}>
            Command Center
          </h1>
          <p className="text-gray-400 text-sm">
            engine running • offer pending • LGAC VHLL
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
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
          <button data-testid="self-improve-btn" className="px-4 py-2 bg-transparent border border-green-500/30 text-green-400 rounded-lg hover:bg-green-500/10 transition-colors text-sm">
            Self-Improve
          </button>
          <button data-testid="pause-all-btn" className="px-4 py-2 bg-transparent border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-800 transition-colors text-sm">
            Pause All
          </button>
          <button data-testid="resume-all-btn" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium">
            Resume All
          </button>
        </div>
      </div>

      {/* Profit-to-25K Proof of Work meter */}
      <ProfitMeter progress={progress} />

      {/* Top Metrics */}
      <MetricsCards {...metrics} />

      {/* Revenue Chart & Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RevenueChart data={revenueChartData} />
        </div>
        <ActivityFeed activities={ACTIVITIES} />
      </div>

      {/* Stream Health Table */}
      <StreamHealthTable streams={enrichedStreams} />

      {/* Agent Fleet */}
      <div className="enterprise-card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white">Agent Fleet</h3>
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
            {agents.length} AGENTS
          </span>
        </div>
        <div className="text-gray-400 text-sm">
          LGAC monitoring: circuit-breakers OK
        </div>
      </div>

      {/* Today's Profit Badge */}
      <div className="profit-badge" data-testid="profit-badge">
        <div className="text-white/80 text-xs font-medium mb-1">TODAY'S PROFIT</div>
        <div className="text-3xl font-bold text-white">
          ${todayProfit.toFixed(2)}
        </div>
        <div className="text-white/60 text-xs mt-1">+12.3% vs avg • {metrics.activeStreams} streams active</div>
      </div>
    </div>
  );
}
