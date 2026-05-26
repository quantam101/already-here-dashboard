import { TrendingUp } from "lucide-react";

function MetricCard({ label, value, change, changeIcon, valueColor, changeColor, testId }) {
  return (
    <div className="metric-card-enterprise" data-testid={testId}>
      <div className="text-gray-400 text-sm mb-2">{label}</div>
      <div className={`text-3xl font-bold ${valueColor} mb-1`}>{value}</div>
      <div className={`flex items-center gap-1 ${changeColor} text-sm`}>
        {changeIcon}
        {change}
      </div>
    </div>
  );
}

export default function MetricsCards({ mrr, mrrGrowth, activeStreams, totalStreams, contentToday, totalAgentRuns }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <MetricCard
        label="REVENUE MRR"
        value={`$${mrr.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
        change={`+${mrrGrowth.toFixed(1)}% vs last month`}
        changeIcon={<TrendingUp className="w-4 h-4" />}
        valueColor="text-green-400"
        changeColor="text-green-400"
        testId="metric-revenue-mrr"
      />
      <MetricCard
        label="ACTIVE STREAMS"
        value={`${activeStreams} / ${totalStreams}`}
        change="running, 0 errors"
        valueColor="text-white"
        changeColor="text-blue-400"
        testId="metric-active-streams"
      />
      <MetricCard
        label="CONTENT / 24H"
        value={contentToday}
        change={`blogs + social, ${activeStreams} platforms`}
        valueColor="text-cyan-400"
        changeColor="text-gray-400"
        testId="metric-content-24h"
      />
      <MetricCard
        label="AI AGENTS / CYCLE"
        value={totalAgentRuns.toLocaleString()}
        change="continuously self-improving"
        valueColor="text-blue-400"
        changeColor="text-gray-400"
        testId="metric-ai-agents"
      />
    </div>
  );
}
