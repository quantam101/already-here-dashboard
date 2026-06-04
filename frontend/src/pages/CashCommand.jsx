import { useQuery } from "@tanstack/react-query";

const API = process.env.REACT_APP_BACKEND_URL || "";

async function fetchCashCommand() {
  const res = await fetch(`${API}/api/cash-command`);
  if (!res.ok) throw new Error("Failed to load Cash Command");
  return res.json();
}

function StatCard({ label, value, sub, color = "blue" }) {
  const colors = {
    blue: "bg-blue-50 border-blue-200 text-blue-700",
    green: "bg-green-50 border-green-200 text-green-700",
    yellow: "bg-yellow-50 border-yellow-200 text-yellow-700",
    red: "bg-red-50 border-red-200 text-red-700",
  };
  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm font-medium mt-1">{label}</div>
      {sub && <div className="text-xs opacity-70 mt-1">{sub}</div>}
    </div>
  );
}

function ScoreDot({ score }) {
  const color =
    score >= 80 ? "bg-green-500" : score >= 50 ? "bg-yellow-400" : "bg-red-400";
  return <span className={`inline-block w-2 h-2 rounded-full ${color} mr-2`} />;
}

export default function CashCommand() {
  const { data, isLoading, error, dataUpdatedAt } = useQuery({
    queryKey: ["cash-command"],
    queryFn: fetchCashCommand,
    refetchInterval: 60000,
  });

  if (isLoading) {
    return (
      <div className="p-6 text-gray-400 text-sm text-center">
        Loading Daily Cash Command...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-red-500 text-sm text-center">
        Failed to load: {error.message}
      </div>
    );
  }

  const {
    work_orders_pending = {},
    revenue_7d = {},
    top_opportunities = [],
    alerts = [],
    action_items = [],
    config = {},
  } = data || {};

  const refreshed = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : "—";

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Daily Cash Command</h1>
          <p className="text-sm text-gray-500 mt-1">
            {config.base_market} · {config.radius_miles}mi radius · ${config.minimum_hourly}/hr min
          </p>
        </div>
        <div className="text-xs text-gray-400">Refreshed {refreshed}</div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 space-y-1">
          <div className="text-sm font-semibold text-red-700 mb-2">Alerts</div>
          {alerts.map((a, i) => (
            <div key={i} className="text-sm text-red-600 flex items-start gap-1">
              <span className="mt-0.5">⚠</span>
              <span>{a}</span>
            </div>
          ))}
        </div>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Pending Work Orders"
          value={work_orders_pending.total ?? 0}
          color="blue"
        />
        <StatCard
          label="Strong Match"
          value={work_orders_pending.strong_match ?? 0}
          sub="Score ≥ 80"
          color="green"
        />
        <StatCard
          label="Counteroffer"
          value={work_orders_pending.counteroffer ?? 0}
          sub="Score 50–79"
          color="yellow"
        />
        <StatCard
          label="Revenue (7d)"
          value={`$${(revenue_7d.total_usd ?? 0).toLocaleString()}`}
          sub="Last 7 days"
          color="green"
        />
      </div>

      {/* Action Items */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 space-y-2">
        <h2 className="font-semibold text-gray-800">Action Items</h2>
        {action_items.map((item, i) => (
          <div
            key={i}
            className="flex items-start gap-2 p-2 rounded-lg bg-gray-50 text-sm text-gray-700"
          >
            <span className="text-blue-500 font-bold mt-0.5">{i + 1}.</span>
            <span>{item}</span>
          </div>
        ))}
      </div>

      {/* Top Opportunities */}
      {top_opportunities.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Top Opportunities</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {top_opportunities.map((opp) => (
              <div key={opp.id} className="p-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center">
                    <ScoreDot score={opp.score} />
                    <span className="font-medium text-gray-900 truncate">{opp.title}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5 pl-4">
                    {opp.company && `${opp.company} · `}
                    {opp.location && `${opp.location} · `}
                    <span className="capitalize">{opp.category}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 pl-4 sm:pl-0">
                  <div className="text-sm font-medium text-gray-700">
                    {opp.rate_offered
                      ? `$${opp.rate_offered}${opp.rate_type === "hourly" ? "/hr" : " flat"}`
                      : "Rate TBD"}
                  </div>
                  <div
                    className={`text-xs font-semibold px-2 py-0.5 rounded ${
                      opp.score >= 80
                        ? "bg-green-100 text-green-700"
                        : opp.score >= 50
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {opp.score}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {top_opportunities.length === 0 && (
        <div className="bg-gray-50 rounded-xl border border-dashed border-gray-200 p-8 text-center text-gray-400 text-sm">
          No scored work orders yet. Use the Work Orders page to add and score opportunities.
        </div>
      )}
    </div>
  );
}
