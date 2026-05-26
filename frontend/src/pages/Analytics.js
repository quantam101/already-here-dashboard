import { useQuery, useMutation } from "@tanstack/react-query";
import { Brain, RefreshCw, Sparkles, TrendingUp, Clock, BarChart3, Share2, Zap } from "lucide-react";
import { analyticsAPI, advisorAPI, paymentsAPI, distillationAPI } from "../lib/api";
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
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 4, left: -24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 9 }} />
              <YAxis tick={{ fill: "#9ca3af", fontSize: 9 }} />
              <Tooltip contentStyle={{ background: "#0f1419", border: "1px solid #1f2937", color: "#fff" }} />
              <Line type="monotone" dataKey="net" stroke="#22c55e" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-xs text-gray-500">
            No data yet · log earnings to see the curve
          </div>
        )}
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

function UTMAttributionCard() {
  const { data: stats } = useQuery({
    queryKey: ["paymentStats"],
    queryFn: () => paymentsAPI.stats().then((r) => r.data),
    refetchInterval: 60000,
  });
  const sources = stats?.by_utm_source || {};
  const rows = Object.entries(sources)
    .map(([source, v]) => ({ source, ...v }))
    .sort((a, b) => b.paid_usd - a.paid_usd);

  return (
    <div className="enterprise-card" data-testid="utm-attribution-card">
      <h3 className="text-base font-semibold text-white mb-1 flex items-center gap-2">
        <Share2 className="w-4 h-4 text-cyan-400" /> Channel Attribution (UTM)
      </h3>
      <p className="text-xs text-gray-400 mb-3">
        Paid sales credited to each share-link source. Generate links on{" "}
        <a href="/pricing" className="text-cyan-300 hover:underline">/pricing</a>.
      </p>
      {rows.length === 0 ? (
        <p className="text-sm text-gray-500">
          No paid transactions yet. Generate a share-link on the Pricing page and post it to start tracking.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left py-2 px-2 text-xs text-gray-400 uppercase tracking-wider">Source</th>
                <th className="text-right py-2 px-2 text-xs text-gray-400 uppercase tracking-wider">Clicks</th>
                <th className="text-right py-2 px-2 text-xs text-gray-400 uppercase tracking-wider">Paid</th>
                <th className="text-right py-2 px-2 text-xs text-gray-400 uppercase tracking-wider">Revenue</th>
                <th className="text-right py-2 px-2 text-xs text-gray-400 uppercase tracking-wider">CVR</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const cvr = r.clicks > 0 ? Math.round((r.paid / r.clicks) * 1000) / 10 : 0;
                return (
                  <tr key={r.source} className="border-b border-white/5" data-testid={`utm-row-${r.source}`}>
                    <td className="py-2 px-2 text-white capitalize">{r.source}</td>
                    <td className="py-2 px-2 text-right text-gray-300">{r.clicks}</td>
                    <td className="py-2 px-2 text-right text-yellow-400">{r.paid}</td>
                    <td className="py-2 px-2 text-right text-green-400 font-semibold">${r.paid_usd}</td>
                    <td className="py-2 px-2 text-right text-cyan-300">{cvr}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
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

function DistillationCard() {
  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ["distillationStats"],
    queryFn: () => distillationAPI.stats().then((r) => r.data),
    refetchInterval: 60000,
  });
  const { data: budget, refetch: refetchBudget } = useQuery({
    queryKey: ["distillationBudget"],
    queryFn: () => distillationAPI.budget().then((r) => r.data),
    refetchInterval: 60000,
  });
  const { data: history, refetch: refetchHistory } = useQuery({
    queryKey: ["distillationHistory"],
    queryFn: () => distillationAPI.budgetHistory(14).then((r) => r.data),
    refetchInterval: 60000,
  });

  const refetch = () => { refetchStats(); refetchBudget(); refetchHistory(); };

  const tokensSaved = stats?.tokens_saved_est ?? 0;
  const usdSaved = stats?.usd_saved_est ?? 0;
  const rows = stats?.rows ?? 0;
  const hits = stats?.hits ?? 0;
  const cap = budget?.daily_cap ?? 0;
  const used = budget?.tokens_total ?? 0;
  const remaining = budget?.remaining;
  const capPct = cap > 0 ? Math.min(100, Math.round((used / cap) * 100)) : 0;

  // Build hit-rate per day from history (oldest → newest for left-to-right chart)
  const chartData = (history ?? [])
    .slice()
    .reverse()
    .map((d) => {
      const calls = Number(d.calls || 0);
      const hits = Number(d.cache_hits || 0);
      const total = calls;  // calls includes cache hits — every call increments `calls`
      const rate = total > 0 ? Math.round((hits / total) * 100) : 0;
      return { date: (d.date || "").slice(5), hit_rate: rate, calls: total };
    });
  const avgHitRate = chartData.length
    ? Math.round(chartData.reduce((s, p) => s + p.hit_rate, 0) / chartData.length)
    : 0;

  return (
    <div className="enterprise-card" data-testid="distillation-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-white flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" /> Data Distillation
          <span className="text-[10px] uppercase tracking-wider text-amber-300/70 ml-1">cost guard</span>
        </h3>
        <Button onClick={refetch} variant="outline" size="sm"
          className="border-amber-500/30 text-amber-300 hover:bg-amber-500/10 h-7 px-2"
          data-testid="distillation-refresh-btn">
          <RefreshCw className="w-3 h-3 mr-1" /> refresh
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-3 mb-3">
        <div className="stat-card" data-testid="distillation-tokens-saved">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">Tokens saved</p>
          <p className="text-xl font-bold text-amber-300">{tokensSaved.toLocaleString()}</p>
        </div>
        <div className="stat-card" data-testid="distillation-usd-saved">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">$ saved (est)</p>
          <p className="text-xl font-bold text-green-300">${usdSaved.toFixed(4)}</p>
        </div>
        <div className="stat-card" data-testid="distillation-cache-rows">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">Cache rows</p>
          <p className="text-xl font-bold text-white">{rows}</p>
        </div>
        <div className="stat-card" data-testid="distillation-cache-hits">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">Cache hits</p>
          <p className="text-xl font-bold text-cyan-300">{hits}</p>
        </div>
      </div>

      <div className="text-xs text-gray-300 mb-1 flex items-center justify-between">
        <span>
          Today: <span className="text-white font-semibold">{used.toLocaleString()}</span> tokens
          {cap > 0 ? ` / ${cap.toLocaleString()} cap` : ""}
        </span>
        <span className="text-gray-400">
          {cap > 0 ? `${(remaining ?? 0).toLocaleString()} remaining` : "no daily cap set"}
        </span>
      </div>
      {cap > 0 && (
        <div className="w-full bg-black/40 rounded h-2 overflow-hidden mb-3">
          <div className={`h-full transition-all ${capPct >= 90 ? "bg-red-500" : capPct >= 60 ? "bg-amber-400" : "bg-emerald-500"}`}
               style={{ width: `${capPct}%` }} />
        </div>
      )}

      {chartData.length > 0 && (
        <div className="mt-3" data-testid="distillation-hitrate-chart">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>Cache hit rate — last {chartData.length} days</span>
            <span className="text-cyan-300 font-semibold">{avgHitRate}% avg</span>
          </div>
          <ResponsiveContainer width="100%" height={90}>
            <LineChart data={chartData} margin={{ top: 5, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#222" />
              <XAxis dataKey="date" stroke="#666" tick={{ fontSize: 10 }} />
              <YAxis domain={[0, 100]} stroke="#666" tick={{ fontSize: 10 }}
                tickFormatter={(v) => `${v}%`} />
              <Tooltip contentStyle={{ background: "#0a0e1a", border: "1px solid #444", fontSize: 11 }}
                formatter={(v, n) => n === "hit_rate" ? [`${v}%`, "Hit rate"] : [v, n]} />
              <Line type="monotone" dataKey="hit_rate" stroke="#22d3ee" strokeWidth={2}
                dot={{ r: 2, fill: "#22d3ee" }} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <p className="text-[10px] text-gray-500 mt-2 leading-snug">
        Semantic compression + YAML payloads + sha256 prompt cache. Set
        <code className="text-amber-300 mx-1">LLM_DAILY_TOKEN_CAP</code>
        to enforce a hard ceiling (returns 429 when exceeded).
      </p>
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

      <DistillationCard />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AdvisorCard />
        <MomentumCard data={data?.momentum} />
        <FunnelCard funnel={data?.funnel} />
        <PostingTimesCard data={data?.posting_times} />
        <StreamROITable data={data?.stream_roi} />
        <PlatformMixCard data={data?.platform_mix} />
        <UTMAttributionCard />
        <ViralThemesCard data={data?.viral_themes} />
      </div>
    </div>
  );
}
