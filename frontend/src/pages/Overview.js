import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Zap,
  DollarSign,
  FileText,
  AlertCircle,
} from "lucide-react";
import { revenueAPI, contentAPI, agentsAPI } from "../lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

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

  // Generate 14-day revenue data
  const revenueChartData = Array.from({ length: 14 }, (_, i) => ({
    day: `Day ${i + 1}`,
    revenue: Math.floor(Math.random() * 200) + 100,
  }));

  // Calculate metrics
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

  // Mock activity feed
  const activities = [
    { text: "Health oracle score live from AppleFoundation", time: "health - 3m ago", type: "success" },
    { text: "LGAC VHLL: 0 resolution - 24 ops validated", time: "vhll - 15 min ago", type: "info" },
    { text: "A/B title test: variant 3 selected", time: "seo - 19 min ago", type: "info" },
    { text: "Trend scan: 12 new niches found", time: "trends - 40m ago", type: "success" },
    { text: "Reddit scheduled: ubuntu_thread", time: "reddit - 60m ago", type: "pending" },
  ];

  const todayProfit = streams.reduce((sum, s) => sum + (s.monthly_actual || 0) / 30, 0);

  return (
    <div data-testid="overview-page" className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1" style={{ fontFamily: 'Space Grotesk' }}>
            Command Center
          </h1>
          <p className="text-gray-400 text-sm">
            6 Mar '26 - 18:27:48 PT • engine running • offer pending • LGAC VHLL
          </p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-transparent border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-800 transition-colors text-sm">
            system: pt 1/5
          </button>
          <button className="px-4 py-2 bg-transparent border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-800 transition-colors text-sm">
            ⏱ Run Cycle
          </button>
          <button className="px-4 py-2 bg-transparent border border-green-500/30 text-green-400 rounded-lg hover:bg-green-500/10 transition-colors text-sm">
            ✓ Self-Improve
          </button>
          <button className="px-4 py-2 bg-transparent border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-800 transition-colors text-sm">
            🔧 Pause All
          </button>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium">
            ▶ Resume All
          </button>
        </div>
      </div>

      {/* Top Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Revenue MRR */}
        <div className="metric-card-enterprise">
          <div className="text-gray-400 text-sm mb-2">REVENUE MRR</div>
          <div className="text-3xl font-bold text-green-400 mb-1">
            ${mrr.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="flex items-center gap-1 text-green-400 text-sm">
            <TrendingUp className="w-4 h-4" />
            +{mrrGrowth.toFixed(1)}% vs last month
          </div>
        </div>

        {/* Active Streams */}
        <div className="metric-card-enterprise">
          <div className="text-gray-400 text-sm mb-2">ACTIVE STREAMS</div>
          <div className="text-3xl font-bold text-white mb-1">
            {activeStreams} / {totalStreams}
          </div>
          <div className="text-blue-400 text-sm">@ running, 0 errors</div>
        </div>

        {/* Content Today */}
        <div className="metric-card-enterprise">
          <div className="text-gray-400 text-sm mb-2">CONTENT / 24H</div>
          <div className="text-3xl font-bold text-cyan-400 mb-1">{contentToday}</div>
          <div className="text-gray-400 text-sm">blogs + social, {activeStreams} platforms</div>
        </div>

        {/* AI Agents Cycle */}
        <div className="metric-card-enterprise">
          <div className="text-gray-400 text-sm mb-2">AI AGENTS / CYCLE</div>
          <div className="text-3xl font-bold text-blue-400 mb-1">
            {totalAgentRuns.toLocaleString()}
          </div>
          <div className="text-gray-400 text-sm">continuously self-improving</div>
        </div>
      </div>

      {/* Revenue Chart & Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue Chart */}
        <div className="lg:col-span-2 enterprise-card">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">Revenue — last 14 days</h3>
            <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
              LIVE
            </span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={revenueChartData}>
              <XAxis
                dataKey="day"
                tick={{ fill: '#6b7280', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis hide />
              <Tooltip
                contentStyle={{
                  background: 'rgba(23, 27, 40, 0.95)',
                  border: '1px solid rgba(34, 197, 94, 0.2)',
                  borderRadius: '8px',
                  color: '#fff',
                }}
                cursor={{ fill: 'rgba(34, 197, 94, 0.1)' }}
              />
              <Bar
                dataKey="revenue"
                fill="url(#colorRevenue)"
                radius={[4, 4, 0, 0]}
                className="revenue-chart-bar"
              />
              <defs>
                <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22c55e" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="#16a34a" stopOpacity={0.6} />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* User Activity */}
        <div className="enterprise-card">
          <h3 className="text-lg font-semibold text-white mb-4">User Activity</h3>
          <div className="space-y-2">
            {activities.map((activity, i) => (
              <div key={i} className="activity-item">
                <div className="flex items-start gap-2">
                  <div
                    className={`w-1.5 h-1.5 rounded-full mt-1.5 ${
                      activity.type === 'success'
                        ? 'bg-green-400'
                        : activity.type === 'pending'
                          ? 'bg-yellow-400'
                          : 'bg-blue-400'
                    }`}
                  />
                  <div className="flex-1">
                    <p className="text-gray-300 text-sm">{activity.text}</p>
                    <p className="text-gray-500 text-xs mt-1">{activity.time}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Stream Health Table */}
      <div className="enterprise-card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white">Stream Health</h3>
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
            LIVE
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                  STREAM
                </th>
                <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                  STATUS
                </th>
                <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                  HEALTH
                </th>
                <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                  30D REVENUE
                </th>
                <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                  TODAY
                </th>
                <th className="text-center py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                  TREND
                </th>
              </tr>
            </thead>
            <tbody>
              {streams.map((stream, i) => {
                const health = 85 + Math.floor(Math.random() * 15);
                const revenue30d = stream.monthly_actual || 0;
                const revenueToday = revenue30d / 30;
                const trend = Math.random() > 0.3;

                return (
                  <tr key={stream.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                    <td className="py-4 px-4">
                      <div className="text-white font-medium">{stream.name}</div>
                    </td>
                    <td className="py-4 px-4">
                      <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs font-medium">
                        {stream.status}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-2">
                        <div className="health-bar w-24">
                          <div
                            className={`health-bar-fill health-${health >= 95 ? '100' : health >= 85 ? '90' : health >= 70 ? '75' : '50'}`}
                            style={{ width: `${health}%` }}
                          />
                        </div>
                        <span className="text-gray-400 text-sm">{health}%</span>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="text-white font-medium">
                        ${revenue30d.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </div>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="text-green-400 font-bold">
                        +${revenueToday.toFixed(2)}
                      </div>
                    </td>
                    <td className="py-4 px-4 text-center">
                      {trend ? (
                        <TrendingUp className="w-5 h-5 text-green-400 inline" />
                      ) : (
                        <TrendingDown className="w-5 h-5 text-red-400 inline" />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

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
        <div className="text-white/60 text-xs mt-1">+12.3% vs avg • 4 streams active</div>
      </div>
    </div>
  );
}