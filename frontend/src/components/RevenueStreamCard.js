import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";

export default function RevenueStreamCard({ stream, onDelete }) {
  const target = stream.monthly_target || 0;
  const actual = stream.monthly_actual || 0;
  const pct = target > 0 ? Math.min(100, Math.round((actual / target) * 100)) : 0;

  return (
    <div
      className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-xl p-5 hover:border-green-500/30 transition-colors"
      data-testid={`stream-${stream.id}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-base font-semibold text-white mb-1 truncate">{stream.name}</h4>
          <div className="flex flex-wrap items-center gap-2">
            <span className="content-badge bg-blue-500/15 text-blue-300 border border-blue-500/20">
              {stream.type}
            </span>
            <span className={`content-badge status-badge-${stream.status}`}>
              {stream.status}
            </span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onDelete(stream.id)}
          className="text-gray-400 hover:text-red-400 hover:bg-red-500/10 shrink-0"
          data-testid={`delete-stream-${stream.id}`}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>

      {stream.description && (
        <p className="text-sm text-gray-400 mb-4 line-clamp-2">{stream.description}</p>
      )}

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Target</p>
          <p className="text-lg font-semibold text-white">${target.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Actual</p>
          <p className="text-lg font-semibold text-green-400">${actual.toLocaleString()}</p>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-gray-500">Progress</span>
          <span className="text-xs text-gray-400 font-medium">{pct}%</span>
        </div>
        <div className="health-bar w-full">
          <div
            className={`health-bar-fill ${pct >= 75 ? "health-100" : pct >= 50 ? "health-90" : pct >= 25 ? "health-75" : "health-50"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
