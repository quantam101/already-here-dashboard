import { useQuery, useMutation } from "@tanstack/react-query";
import { Brain, RefreshCw, Sparkles, TrendingUp, Clock, BarChart3 } from "lucide-react";
import { analyticsAPI, advisorAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
} from "recharts";

function StatTile({ label, value, accent = "text-white", testId }) {
  return (
    <div className="stat-card" data-testid={testId}>
      <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">{label}</p>
      <p className={`text-2xl font-bold ${accent}`}>{value}</p>
    </div>
  );
}

function FunnelCard({ funnel }) {
  if (!funnel) return null;
  const stages = [
    { key: "drafted", label: "Drafted", accent: "text-gray-300" },
    { key: "exported", label: "Exported", accent: "text-blue-400" },
    { key: "posted", label: "Posted", accent: "text-yellow-400" },
    { key: "verified", label: "Verified", accent: "text-green-400" },
  ];
  return (
    <div className="enterprise-card">
      <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-blue-400" /> Conversion Funnel
      </h3>
      <div className="grid grid-cols-4 gap-3 mb-4">
        {stages.map((s) => (
          <div key={s.key} className="text-center" data-testid={`funnel-${s.key}`}>
            <p className={`text-3xl font-bold ${s.accent}`}>{funnel.totals?.[s.key] || 0}</p>
            <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">{s.label}</p>
          </div>
        ))}
      </div>
      <div className="text-xs text-gray-400 space-y-1">
        <div>Drafted → Exported: <span className="text-blue-400 font-semibold">{funnel.rates?.drafted_to_exported}%</span></div>
        <div>Exported → Posted: <span className="text-yellow-400 font-semibold">{funnel.rates?.exported_to_posted}%</span></div>
        <div>Posted → Verified: <span className="text-green-400 font-semibold">{funnel.rates?.posted_to_verified}%</span></div>
      </div>
    </div>
  );
}

function PostingTimesCard({ data }) {
  if (!data) return null;
  const chartData = Array.from({ length: 24 }, (_, h) => ({
    hour: `${h.toString().padStart(2, "0")}h`,
    posts: data.posts_by_hour_utc?.[h] || 0,
  }));
  return (
    <div className="enterprise-card">
      <h3 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
        <Clock className="w-4 h-4 text-yellow-400" /> Best Posting Times (UTC)
      </h3>
      <p className="text-xs text-green-400 mb-3" data-testid="posting-recommendation">{data.recommendation}</p>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 4, left: -24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="hour" tick={{ fill: "#9ca3af", fontSize: 10 }} interval={3} />
            <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
            <Tooltip contentStyle={{ background: "#0f1419", border: "1px solid #1f2937", color: "#fff" }} />
            <Bar dataKey="posts" fill="#22c55e" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function StreamROITable({ data }) {
  if (!data?.streams) return null;
  return (
    <div className="enterprise-card">
      <h3 className="text-base font-semibold text-white mb-3">Stream ROI</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left py-2 px-2 text-xs text-gray-400 uppercase tracking-wider">Stream</th>
              <th className="text-right py-2 px-2 text-xs text-gray-400 uppercase tracking-wider">Net</th>
              <th className="text-right py-2 px-2 text-xs text-gray-400 uppercase tracking-wider">Posts</th>
              <th className="text-right py-2 px-2 text-xs text-gray-400 uppercase tracking-wider">$/Post</th>
            </tr>
          </thead>
          <tbody>
            {data.streams.slice(0, 8).map((s) => (
              <tr key={s.stream_id} className="border-b border-white/5">
                <td className="py-2 px-2 text-white truncate max-w-[180px]">{s.name}</td>
                <td className="py-2 px-2 text-right text-green-400 font-semibold">${s.net_total}</td>
                <td className="py-2 px-2 text-right text-gray-300">{s.post_count}</td>
                <td className="py-2 px-2 text-right text-blue-400">${s.revenue_per_post}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MomentumCard({ data }) {
  if (!data) return null;
  const chartData = data.trend_by_day || [];
  return (
    <div className="enterprise-card">
      <h3 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-green-400" /> Revenue Momentum (30d)
      </h3>
      <p className="text-xs text-green-400 mb-3">{data.recommendation}</p>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <StatTile label="Last 30d" value={`$${data.last_30_days_net}`} accent="text-blue-400" />
        <StatTile label="Last 7d" value={`$${data.last_7_days_net}`} accent="text-purple-400" />
        <StatTile label="$/day" value={`$${data.daily_avg_last_7d}`} accent="text-yellow-400" />
      </div>
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 4, left: -24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 9 }} />
            <YAxis tick={{ fill: "#9ca3af", fontSize: 9 }} />
            <Tooltip contentStyle={{ background: "#0f1419", border: "1px solid #1f2937", color: "#fff" }} />
            <Line type="monotone" dataKey="net" stroke="#22c55e" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ViralThemesCard({ data }) {
  if (!data?.top_themes) return null;
  return (
    <div className="enterprise-card">
      <h3 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-purple-400" /> Trending Themes
      </h3>
      <p className="text-xs text-green-400 mb-3" data-testid="viral-recommendation">{data.recommendation}</p>
      <div className="flex flex-wrap gap-2">
        {data.top_themes.slice(0, 15).map((t) => (
          <span
            key={t.word}
            className="content-badge bg-purple-500/15 text-purple-300 border border-purple-500/20"
            style={{ fontSize: `${Math.min(16, 10 + t.count)}px` }}
          >
            {t.word} · {t.count}
          </span>
        ))}
      </div>
    </div>
  );
}

function PlatformMixCard({ data }) {
  if (!data?.platforms) return null;
  return (
    <div className="enterprise-card">
      <h3 className="text-base font-semibold text-white mb-3">Platform Mix</h3>
      <div className="space-y-2">
        {data.platforms.slice(0, 6).map((p) => (
          <div key={p.platform} className="flex items-center justify-between text-sm">
            <span className="text-white capitalize">{p.platform}</span>
            <div className="flex items-center gap-3 text-xs">
              <span className="text-gray-400">{p.posts} posts</span>
              <span className="text-green-400">{p.verification_rate}% verified</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AdvisorCard() {
  const { data: recent = [] } = useQuery({
    queryKey: ["advisorRecent"],
    queryFn: () => advisorAPI.recent().then((r) => r.data),
  });
  const ask = useMutation({
    mutationFn: () => advisorAPI.recommend(),
    onSuccess: () => toast.success("Advisor returned a recommendation"),
    onError: (err) => toast.error(err?.response?.data?.detail || err.message),
  });

  const latest = ask.data?.data || recent[0];
  return (
    <div className="enterprise-card lg:col-span-2">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-white flex items-center gap-2">
          <Brain className="w-4 h-4 text-pink-400" /> AI Operations Advisor (Claude Sonnet)
        </h3>
        <Button
          onClick={() => ask.mutate()}
          disabled={ask.isPending}
          variant="outline"
          className="border-pink-500/30 text-pink-300 hover:bg-pink-500/10"
          data-testid="advisor-ask"
        >
          <RefreshCw className={`w-4 h-4 mr-1.5 ${ask.isPending ? "animate-spin" : ""}`} />
          {ask.isPending ? "Thinking..." : "Get Recommendation"}
        </Button>
      </div>
      {!latest ? (
        <p className="text-sm text-gray-400">
          Click <span className="text-pink-400 font-medium">Get Recommendation</span> — Claude
          reads your live dashboard (funnel, ROI, momentum, themes) and returns one next-best action.
        </p>
      ) : (
        <div className="space-y-3" data-testid="advisor-card">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Headline</p>
            <p className="text-white font-semibold">{latest.headline}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Next Action</p>
            <p className="text-green-400">{latest.next_action}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Why</p>
            <p className="text-sm text-gray-300">{latest.rationale}</p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className={`content-badge ${latest.confidence === "high" ? "status-badge-active" : latest.confidence === "low" ? "status-badge-failed" : "status-badge-pending"}`}>
              {latest.confidence} confidence
            </span>
            <span className="text-gray-500">$0 cost · {new Date(latest.generated_at).toLocaleString()}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Analytics() {
  const { data, isFetching, refetch } = useQuery({
    queryKey: ["analyticsDashboard"],
    queryFn: () => analyticsAPI.dashboard().then((r) => r.data),
  });

  return (
    <div data-testid="analytics-page" className="p-6 dark-themed-page space-y-6">
      <div className="page-header flex items-center justify-between gap-4">
        <div>
          <h1>Analytics</h1>
          <p>Live dashboard - posting times, ROI, momentum, themes. Decisions backed by data.</p>
        </div>
        <Button onClick={() => refetch()} disabled={isFetching}
          variant="outline" className="border-green-500/30 text-green-300 hover:bg-green-500/10">
          <RefreshCw className={`w-4 h-4 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AdvisorCard />
        <MomentumCard data={data?.momentum} />
        <FunnelCard funnel={data?.funnel} />
        <PostingTimesCard data={data?.posting_times} />
        <StreamROITable data={data?.stream_roi} />
        <PlatformMixCard data={data?.platform_mix} />
        <ViralThemesCard data={data?.viral_themes} />
      </div>
    </div>
  );
}
