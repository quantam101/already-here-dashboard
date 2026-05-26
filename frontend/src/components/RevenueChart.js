import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import {
  CHART_TICK_STYLE,
  CHART_TOOLTIP_STYLE,
  CHART_CURSOR_STYLE,
  CHART_BAR_RADIUS,
} from "../lib/chartConfig";

export default function RevenueChart({ data }) {
  return (
    <div className="enterprise-card" data-testid="revenue-chart">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Revenue — last 14 days</h3>
        <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
          LIVE
        </span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data}>
          <XAxis dataKey="day" tick={CHART_TICK_STYLE} axisLine={false} tickLine={false} />
          <YAxis hide />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={CHART_CURSOR_STYLE} />
          <Bar dataKey="revenue" fill="url(#colorRevenue)" radius={CHART_BAR_RADIUS} />
          <defs>
            <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22c55e" stopOpacity={0.9} />
              <stop offset="100%" stopColor="#16a34a" stopOpacity={0.6} />
            </linearGradient>
          </defs>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
