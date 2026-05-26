import { TrendingUp, TrendingDown } from "lucide-react";
import {
  HEALTH_THRESHOLD_EXCELLENT,
  HEALTH_THRESHOLD_GOOD,
  HEALTH_THRESHOLD_FAIR,
  DAYS_PER_MONTH,
} from "../lib/chartConfig";

function getHealthClass(health) {
  if (health >= HEALTH_THRESHOLD_EXCELLENT) return 'health-100';
  if (health >= HEALTH_THRESHOLD_GOOD) return 'health-90';
  if (health >= HEALTH_THRESHOLD_FAIR) return 'health-75';
  return 'health-50';
}

function StreamRow({ stream }) {
  const health = stream.health || HEALTH_THRESHOLD_GOOD;
  const revenue30d = stream.monthly_actual || 0;
  const revenueToday = revenue30d / DAYS_PER_MONTH;
  const trend = stream.trend !== false;

  return (
    <tr className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors" data-testid={`stream-row-${stream.id}`}>
      <td className="py-4 px-4">
        <div className="text-white font-medium">{stream.name}</div>
      </td>
      <td className="py-4 px-4">
        <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs font-medium">{stream.status}</span>
      </td>
      <td className="py-4 px-4">
        <div className="flex items-center gap-2">
          <div className="health-bar w-24">
            <div className={`health-bar-fill ${getHealthClass(health)}`} style={{ width: `${health}%` }} />
          </div>
          <span className="text-gray-400 text-sm">{health}%</span>
        </div>
      </td>
      <td className="py-4 px-4 text-right">
        <div className="text-white font-medium">${revenue30d.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
      </td>
      <td className="py-4 px-4 text-right">
        <div className="text-green-400 font-bold">+${revenueToday.toFixed(2)}</div>
      </td>
      <td className="py-4 px-4 text-center">
        {trend ? <TrendingUp className="w-5 h-5 text-green-400 inline" /> : <TrendingDown className="w-5 h-5 text-red-400 inline" />}
      </td>
    </tr>
  );
}

export default function StreamHealthTable({ streams }) {
  return (
    <div className="enterprise-card" data-testid="stream-health-table">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Stream Health</h3>
        <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">LIVE</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">STREAM</th>
              <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">STATUS</th>
              <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">HEALTH</th>
              <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">30D REVENUE</th>
              <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">TODAY</th>
              <th className="text-center py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">TREND</th>
            </tr>
          </thead>
          <tbody>
            {streams.map((stream) => (
              <StreamRow key={stream.id} stream={stream} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
