import { motion } from "framer-motion";
import { Trophy, TrendingUp, Lock, Unlock, Zap } from "lucide-react";

const GOAL_USD = 25000;
const RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function ArcProgress({ pct, unlocked }) {
  const offset = CIRCUMFERENCE - (pct / 100) * CIRCUMFERENCE;
  const color = unlocked ? "#22c55e" : pct > 75 ? "#22c55e" : pct > 40 ? "#3b82f6" : "#6366f1";
  const glowColor = unlocked ? "rgba(34,197,94,0.5)" : "rgba(99,102,241,0.4)";

  return (
    <div className="relative flex items-center justify-center" style={{ width: 140, height: 140 }}>
      {/* Outer glow ring */}
      {(unlocked || pct > 20) && (
        <div
          className="absolute rounded-full glow-pulse"
          style={{
            inset: 8,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${glowColor} 0%, transparent 70%)`,
            opacity: 0.35,
          }}
        />
      )}
      <svg width="140" height="140" style={{ transform: "rotate(-90deg)" }}>
        {/* Track */}
        <circle
          cx="70" cy="70" r={RADIUS}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="10"
        />
        {/* Progress arc */}
        <motion.circle
          cx="70" cy="70" r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          initial={{ strokeDashoffset: CIRCUMFERENCE }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.4, ease: "easeOut" }}
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
        {/* Tick at goal */}
        {unlocked && (
          <circle cx="70" cy="70" r={RADIUS} fill="none"
            stroke="#22c55e" strokeWidth="3" opacity="0.3"
            strokeDasharray="2 4"
          />
        )}
      </svg>
      {/* Center text */}
      <div className="absolute text-center">
        {unlocked
          ? <Unlock className="w-6 h-6 text-green-400 mx-auto" />
          : <Trophy className="w-6 h-6 text-yellow-400 mx-auto" />}
        <div className="text-base font-bold text-white mt-0.5">{pct.toFixed(1)}%</div>
      </div>
    </div>
  );
}

export default function ProfitMeter({ progress, compact = false }) {
  const totalNet = progress?.total_net ?? 0;
  const pct = Math.min(100, progress?.progress_pct ?? 0);
  const remaining = progress?.remaining_usd ?? GOAL_USD;
  const unlocked = progress?.unlocked ?? false;
  const monthlyNet = progress?.monthly_net ?? 0;
  const entryCount = progress?.entry_count ?? 0;

  // Projected days to unlock (rough)
  const dailyRate = monthlyNet > 0 ? monthlyNet / 30 : 0;
  const daysToUnlock = dailyRate > 0 ? Math.ceil(remaining / dailyRate) : null;

  if (compact) {
    return (
      <div className="enterprise-card" data-testid="profit-meter-compact">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Trophy className="w-4 h-4 text-yellow-400" />
            <span className="text-sm font-semibold text-white">Profit to $25K</span>
          </div>
          {unlocked
            ? <span className="content-badge status-badge-active"><Unlock className="w-3 h-3" /> UNLOCKED</span>
            : <span className="content-badge status-badge-sovereign"><Lock className="w-3 h-3" /> {pct.toFixed(1)}%</span>}
        </div>
        <div className="flex items-baseline justify-between mb-2">
          <span className="text-2xl font-bold text-white">${totalNet.toLocaleString()}</span>
          <span className="text-xs text-gray-400">/ $25,000</span>
        </div>
        <div className="health-bar w-full mb-1">
          <motion.div
            className={`health-bar-fill ${pct >= 75 ? "health-100" : pct >= 50 ? "health-90" : pct >= 25 ? "health-75" : "health-50"}`}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 1, ease: "easeOut" }}
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
    <motion.div
      className="enterprise-card"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      data-testid="profit-meter-full"
      style={unlocked ? {
        background: "linear-gradient(135deg, rgba(22,163,74,0.12) 0%, rgba(16,185,129,0.06) 100%)",
        borderColor: "rgba(34,197,94,0.3)",
      } : undefined}
    >
      <div className="flex flex-col lg:flex-row gap-6 items-center lg:items-start">
        {/* Arc progress */}
        <div className="flex-shrink-0">
          <ArcProgress pct={pct} unlocked={unlocked} />
        </div>

        {/* Stats */}
        <div className="flex-1 w-full">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <Trophy className="w-5 h-5 text-yellow-400" />
                <h3 className="text-lg font-bold text-white" style={{ fontFamily: "Space Grotesk" }}>
                  Proof-of-Work · $25K Unlock
                </h3>
              </div>
              <p className="text-xs text-gray-400">
                Cumulative <span className="text-green-400 font-semibold">net</span> revenue.
                Reach $25,000 to unlock commercialization.
              </p>
            </div>
            {unlocked
              ? <span className="content-badge status-badge-active text-sm px-3 py-1"><Unlock className="w-3 h-3" /> UNLOCKED</span>
              : <span className="content-badge status-badge-sovereign text-sm px-3 py-1"><Lock className="w-3 h-3" /> LOCKED</span>}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Total Net", value: `$${totalNet.toLocaleString()}`, color: "text-green-400" },
              { label: "This Month", value: `$${monthlyNet.toLocaleString()}`, color: "text-white" },
              { label: "Remaining", value: `$${remaining.toLocaleString()}`, color: "text-blue-400" },
              {
                label: daysToUnlock ? "Days to Unlock" : "Entries",
                value: daysToUnlock ? `~${daysToUnlock}d` : entryCount,
                color: "text-purple-400",
                icon: daysToUnlock ? <Zap className="w-4 h-4 inline mr-1" /> : <TrendingUp className="w-4 h-4 inline mr-1" />,
              },
            ].map(({ label, value, color, icon }) => (
              <div key={label}>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
                <p className={`text-2xl font-bold ${color}`}>{icon}{value}</p>
              </div>
            ))}
          </div>

          {/* Linear bar (redundant but good for scanability) */}
          <div className="mt-4">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>$0</span>
              <span className="font-semibold text-gray-400">{pct.toFixed(2)}% complete</span>
              <span>$25,000</span>
            </div>
            <div className="health-bar" style={{ height: 8 }}>
              <motion.div
                className={`health-bar-fill ${pct >= 75 ? "health-100" : pct >= 50 ? "health-90" : pct >= 25 ? "health-75" : "health-50"}`}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 1.2, ease: "easeOut" }}
              />
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}