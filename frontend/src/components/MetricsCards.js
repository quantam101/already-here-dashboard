import { motion } from "framer-motion";
import { TrendingUp, TrendingDown } from "lucide-react";

function MetricCard({ label, value, change, changeIcon, valueColor, changeColor, testId, delay = 0 }) {
  return (
    <motion.div
      className="metric-card-enterprise"
      data-testid={testId}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: "easeOut" }}
    >
      <div className="text-gray-500 text-xs uppercase tracking-wider mb-2">{label}</div>
      <div className={`text-3xl font-bold ${valueColor} mb-1.5`} style={{ fontFamily: "Space Grotesk" }}>
        {value}
      </div>
      <div className={`flex items-center gap-1 ${changeColor} text-xs`}>
        {changeIcon}
        {change}
      </div>
    </motion.div>
  );
}

export default function MetricsCards({ mrr, mrrGrowth, activeStreams, totalStreams, contentToday, totalAgentRuns }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        label="Revenue MRR"
        value={`$${mrr.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
        change={`+${mrrGrowth.toFixed(1)}% vs last month`}
        changeIcon={<TrendingUp className="w-3.5 h-3.5" />}
        valueColor="text-green-400"
        changeColor="text-green-400"
        testId="metric-revenue-mrr"
        delay={0}
      />
      <MetricCard
        label="Active Streams"
        value={`${activeStreams} / ${totalStreams}`}
        change="running · 0 errors"
        changeIcon={<TrendingUp className="w-3.5 h-3.5" />}
        valueColor="text-white"
        changeColor="text-blue-400"
        testId="metric-active-streams"
        delay={0.05}
      />
      <MetricCard
        label="Content / 24H"
        value={contentToday}
        change={`blogs + social · ${activeStreams} platforms`}
        valueColor="text-cyan-400"
        changeColor="text-gray-400"
        testId="metric-content-24h"
        delay={0.1}
      />
      <MetricCard
        label="Agent Cycles"
        value={totalAgentRuns.toLocaleString()}
        change="sovereign governed · self-improving"
        valueColor="text-indigo-400"
        changeColor="text-gray-400"
        testId="metric-ai-agents"
        delay={0.15}
      />
    </div>
  );
}