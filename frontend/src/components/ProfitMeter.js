import { Trophy, TrendingUp, Lock, Unlock } from "lucide-react";

const GOAL_USD = 25000;

export default function ProfitMeter({ progress, compact = false }) {
  const totalNet = progress?.total_net ?? 0;
  const pct = Math.min(100, progress?.progress_pct ?? 0);
  const remaining = progress?.remaining_usd ?? GOAL_USD;
  const unlocked = progress?.unlocked ?? false;
  const monthlyNet = progress?.monthly_net ?? 0;
  const entryCount = progress?.entry_count ?? 0;

  if (compact) {
    return (
      <div className="enterprise-card" data-testid="profit-meter-compact">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Trophy className="w-4 h-4 text-yellow-400" />
            <span className="text-sm font-semibold text-white">Profit to $25K</span>
          </div>
          {unlocked ? (
            <span className="content-badge status-badge-active flex items-center gap-1">
              <Unlock className="w-3 h-3" /> UNLOCKED
            </span>
          ) : (
            <span className="content-badge bg-yellow-500/15 text-yellow-300 border border-yellow-500/20 flex items-center gap-1">
              <Lock className="w-3 h-3" /> Locked
            </span>
          )}
        </div>
        <div className="flex items-baseline justify-between mb-2">
          <span className="text-2xl font-bold text-white">${totalNet.toLocaleString()}</span>
          <span className="text-xs text-gray-400">/ ${GOAL_USD.toLocaleString()}</span>
        </div>
        <div className="health-bar w-full mb-2">
          <div
            className={`health-bar-fill ${pct >= 75 ? "health-100" : pct >= 50 ? "health-90" : pct >= 25 ? "health-75" : "health-50"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>{pct.toFixed(1)}% complete</span>
          <span>{entryCount} entries</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="enterprise-card relative overflow-hidden"
      data-testid="profit-meter-full"
      style={{
        background: unlocked
          ? "linear-gradient(135deg, rgba(34,197,94,0.18), rgba(16,185,129,0.08))"
          : undefined,
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Trophy className="w-5 h-5 text-yellow-400" />
            <h3 className="text-lg font-semibold text-white">
              Proof-of-Work · Profit to ${GOAL_USD.toLocaleString()}
            </h3>
          </div>
          <p className="text-xs text-gray-400">
            Cumulative <span className="text-green-400 font-semibold">net</span> earnings recorded
            in the immutable ledger. Reach the goal to unlock commercialization.
          </p>
        </div>
        {unlocked ? (
          <span className="content-badge status-badge-active flex items-center gap-1">
            <Unlock className="w-3 h-3" /> UNLOCKED
          </span>
        ) : (
          <span className="content-badge bg-yellow-500/15 text-yellow-300 border border-yellow-500/20 flex items-center gap-1">
            <Lock className="w-3 h-3" /> {pct.toFixed(1)}%
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Total Net</p>
          <p className="text-2xl font-bold text-green-400">${totalNet.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">This Month</p>
          <p className="text-2xl font-bold text-white">${monthlyNet.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Remaining</p>
          <p className="text-2xl font-bold text-blue-400">${remaining.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Entries</p>
          <p className="text-2xl font-bold text-purple-400 flex items-center gap-1.5">
            <TrendingUp className="w-5 h-5" />
            {entryCount}
          </p>
        </div>
      </div>

      <div className="health-bar w-full h-2 mb-2" style={{ height: "10px" }}>
        <div
          className={`health-bar-fill ${pct >= 75 ? "health-100" : pct >= 50 ? "health-90" : pct >= 25 ? "health-75" : "health-50"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>$0</span>
        <span className="text-gray-400 font-medium">{pct.toFixed(1)}% to goal</span>
        <span>${GOAL_USD.toLocaleString()}</span>
      </div>
    </div>
  );
}
