import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { useState } from "react";
import {
  CHART_TICK_STYLE, CHART_BAR_RADIUS,
} from "../lib/chartConfig";

const TOOLTIP_STYLE = {
  background: "#0a0f1e",
  border: "1px solid rgba(34,197,94,0.2)",
  borderRadius: 8,
  color: "#fff",
  fontSize: 12,
};

export default function RevenueChart({ data }) {
  const [mode, setMode] = useState("area");
  return (
    <div className="enterprise-card" data-testid="revenue-chart">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-white">Revenue — last 14 days</h3>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs text-green-400">
            <span className="live-dot" style={{ width: 6, height: 6 }} /> LIVE
          </span>
          <div className="flex rounded-lg overflow-hidden border border-white/10">
            {["area", "bar"].map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className="px-3 py-1 text-xs transition-colors"
                style={{
                  background: mode === m ? "rgba(34,197,94,0.15)" : "transparent",
                  color: mode === m ? "#4ade80" : "#6b7280",
                }}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        {mode === "area" ? (
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
            <defs>
              <linearGradient id="revAreaFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#22c55e" stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="day" tick={CHART_TICK_STYLE} axisLine={false} tickLine={false} />
            <YAxis hide />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Area
              type="monotone" dataKey="revenue"
              stroke="#22c55e" strokeWidth={2}
              fill="url(#revAreaFill)"
            />
          </AreaChart>
        ) : (
          <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="day" tick={CHART_TICK_STYLE} axisLine={false} tickLine={false} />
            <YAxis hide />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <defs>
              <linearGradient id="revBarFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.9} />
                <stop offset="100%" stopColor="#16a34a" stopOpacity={0.6} />
              </linearGradient>
            </defs>
            <Bar dataKey="revenue" fill="url(#revBarFill)" radius={CHART_BAR_RADIUS} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}