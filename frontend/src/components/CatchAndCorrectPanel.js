import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Shield, ChevronDown, ChevronUp, X } from "lucide-react";
import { lcacAPI } from "../lib/api";

// Fixed bottom-right global telemetry side-panel — operationalizes blueprint §8
// "Lifelong Catch and Correct". Polls /api/lifelong-catch-correct/ every 30s and
// surfaces high/medium severity findings. Click to expand the full list.

const SEVERITY_STYLE = {
  high: "border-red-500/40 text-red-300 bg-red-500/5",
  medium: "border-amber-500/40 text-amber-300 bg-amber-500/5",
  low: "border-gray-500/30 text-gray-300 bg-gray-500/5",
};

export default function CatchAndCorrectPanel() {
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  const { data, refetch } = useQuery({
    queryKey: ["lcac"],
    queryFn: () => lcacAPI.scan().then((r) => r.data),
    refetchInterval: 30000,
    enabled: !dismissed,
  });

  if (dismissed) return null;

  const findings = Array.isArray(data) ? data : data?.findings || [];
  const high = findings.filter((f) => f.severity === "high").length;
  const medium = findings.filter((f) => f.severity === "medium").length;
  const low = findings.filter((f) => f.severity === "low").length;
  const total = findings.length;

  if (total === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 max-w-md text-xs"
      data-testid="catch-and-correct-panel"
    >
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg border shadow-lg ${
            high > 0
              ? "border-red-500/50 bg-red-500/10 text-red-300"
              : medium > 0
              ? "border-amber-500/50 bg-amber-500/10 text-amber-300"
              : "border-gray-500/40 bg-gray-500/10 text-gray-300"
          }`}
          data-testid="catch-and-correct-toggle"
        >
          <Shield className="w-3.5 h-3.5" />
          <span className="font-semibold">Catch & Correct</span>
          <span className="text-[10px] opacity-75">
            {high > 0 ? `${high} HIGH · ` : ""}
            {medium > 0 ? `${medium} MED · ` : ""}
            {low > 0 ? `${low} LOW` : ""}
          </span>
          <ChevronUp className="w-3 h-3" />
        </button>
      ) : (
        <div
          className="bg-[#0a0e1a] border border-cyan-500/40 rounded-lg shadow-2xl p-3"
          data-testid="catch-and-correct-expanded"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Shield className="w-3.5 h-3.5 text-cyan-300" />
              <span className="font-semibold text-white">
                Catch & Correct ({total})
              </span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => refetch()}
                className="text-[10px] text-cyan-300 hover:text-cyan-200 px-1"
                data-testid="catch-and-correct-refresh"
              >
                refresh
              </button>
              <button
                onClick={() => setOpen(false)}
                className="text-gray-400 hover:text-white"
                data-testid="catch-and-correct-collapse"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
              <button
                onClick={() => setDismissed(true)}
                className="text-gray-400 hover:text-white"
                data-testid="catch-and-correct-dismiss"
                title="Hide until next page load"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          <p className="text-[10px] text-gray-500 mb-2 leading-snug">
            Live telemetry from the audit ledger, cost guard, and ledger. Click
            an issue for the suggested fix.
          </p>

          <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
            {findings.map((f, i) => (
              <div
                key={i}
                className={`border rounded px-2 py-1.5 ${SEVERITY_STYLE[f.severity] || SEVERITY_STYLE.low}`}
                data-testid={`catch-finding-${i}`}
              >
                <div className="flex items-start gap-1.5">
                  <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold leading-snug">{f.message}</p>
                    {f.suggestion && (
                      <p className="text-[10px] opacity-80 mt-0.5 leading-snug">
                        → {f.suggestion}
                      </p>
                    )}
                    <p className="text-[9px] opacity-60 mt-0.5 uppercase tracking-wider">
                      {f.category} · {f.severity}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
