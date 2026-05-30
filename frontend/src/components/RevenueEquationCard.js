import { useQuery } from "@tanstack/react-query";
import { Target, TrendingUp, AlertTriangle } from "lucide-react";
import { revenueEquationAPI } from "../lib/api";

// Master Revenue Equation card — operationalizes blueprint §2:
//   Daily Revenue Capacity = Q_D × C_R × A_OV × P_F × F_C × P_M
//   north-star target: $1,000,000/day
// Highlights the bottleneck variable in red so the operator knows where to focus.

const VAR_LABEL = {
  Q_D: "Qualified Demand",
  C_R: "Conversion Rate",
  A_OV: "Avg Order Value",
  P_F: "Purchase Freq",
  F_C: "Fulfillment Cap",
  P_M: "Profit Margin",
};
const VAR_FORMAT = {
  Q_D: (v) => `${Number(v).toFixed(2)}/day`,
  C_R: (v) => `${(Number(v) * 100).toFixed(2)}%`,
  A_OV: (v) => `$${Number(v).toFixed(2)}`,
  P_F: (v) => `${Number(v).toFixed(4)}`,
  F_C: (v) => `${Number(v).toFixed(0)}/day`,
  P_M: (v) => `${(Number(v) * 100).toFixed(1)}%`,
};

export default function RevenueEquationCard() {
  const { data, isFetching, refetch } = useQuery({
    queryKey: ["revenueEquation"],
    queryFn: () => revenueEquationAPI.equation().then((r) => r.data),
    refetchInterval: 60000,
  });

  if (!data) {
    return (
      <div className="enterprise-card" data-testid="revenue-equation-card">
        <div className="text-xs text-gray-400">
          Loading Master Revenue Equation…
        </div>
      </div>
    );
  }

  const bn = data.bottleneck || {};
  const pct = Number(data.percent_of_north_star || 0);
  const cap = Number(data.daily_capacity_usd || 0);
  const ns = Number(data.north_star_usd_per_day || 1_000_000);
  const gap = Number(data.gap_to_north_star_usd || 0);

  return (
    <div className="enterprise-card" data-testid="revenue-equation-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-white flex items-center gap-2">
          <Target className="w-4 h-4 text-emerald-300" /> Master Revenue Equation
          <span className="text-[10px] uppercase tracking-wider text-emerald-300/70 ml-1">
            north star
          </span>
        </h3>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="text-xs text-emerald-300 hover:text-emerald-200"
          data-testid="revenue-equation-refresh"
        >
          {isFetching ? "…" : "refresh"}
        </button>
      </div>

      <div className="mb-3 text-[10px] text-gray-400 font-mono">
        {data.formula}
      </div>

      <div className="grid grid-cols-6 gap-2 mb-3">
        {["Q_D", "C_R", "A_OV", "P_F", "F_C", "P_M"].map((k) => {
          const v = data.variables?.[k] ?? 0;
          const isBottleneck = bn.variable === k;
          return (
            <div
              key={k}
              data-testid={`revenue-var-${k.toLowerCase()}`}
              className={`stat-card ${isBottleneck ? "ring-1 ring-red-400/60" : ""}`}
            >
              <p className="text-[9px] text-gray-400 uppercase tracking-wider mb-0.5">
                {VAR_LABEL[k]}
              </p>
              <p className={`text-sm font-bold ${isBottleneck ? "text-red-300" : "text-white"}`}>
                {VAR_FORMAT[k]?.(v) ?? v}
              </p>
              {isBottleneck && (
                <p className="text-[9px] text-red-300 mt-0.5 flex items-center gap-0.5">
                  <AlertTriangle className="w-2.5 h-2.5" /> bottleneck
                </p>
              )}
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="stat-card" data-testid="revenue-capacity">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">
            Today's capacity
          </p>
          <p className="text-xl font-bold text-emerald-300">
            ${cap.toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </p>
          <p className="text-[10px] text-gray-500">USD/day</p>
        </div>
        <div className="stat-card" data-testid="revenue-pct-target">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">
            % of north star
          </p>
          <p className="text-xl font-bold text-cyan-300">
            {pct < 0.001 ? "<0.001" : pct.toFixed(4)}%
          </p>
          <p className="text-[10px] text-gray-500">
            target ${ns.toLocaleString()}/day
          </p>
        </div>
        <div className="stat-card" data-testid="revenue-gap">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">
            Gap to close
          </p>
          <p className="text-xl font-bold text-amber-300">
            ${gap.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
          <p className="text-[10px] text-gray-500 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> per day
          </p>
        </div>
      </div>

      {bn.variable && (
        <p className="mt-3 text-[11px] text-gray-300 bg-red-500/5 border border-red-500/20 rounded px-2 py-1.5">
          <span className="text-red-300 font-semibold">{VAR_LABEL[bn.variable]}</span>{" "}
          is your highest-leverage focus right now —{" "}
          <span className="text-white font-semibold">{bn.gap_percent}%</span> below
          its target of <span className="text-white">{VAR_FORMAT[bn.variable]?.(bn.target)}</span>.
        </p>
      )}
    </div>
  );
}
