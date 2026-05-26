import { AlertCircle, CheckCircle, Lock } from "lucide-react";

const COST_CLASS_CONFIG = {
  free_local: {
    color: "text-green-400",
    bg: "bg-green-500/20",
    border: "border-green-500/30",
    icon: CheckCircle,
    label: "FREE LOCAL",
  },
  free_external: {
    color: "text-blue-400",
    bg: "bg-blue-500/20",
    border: "border-blue-500/30",
    icon: CheckCircle,
    label: "FREE API",
  },
  free_with_limits: {
    color: "text-cyan-400",
    bg: "bg-cyan-500/20",
    border: "border-cyan-500/30",
    icon: AlertCircle,
    label: "FREE LIMITED",
  },
  manual_free: {
    color: "text-yellow-400",
    bg: "bg-yellow-500/20",
    border: "border-yellow-500/30",
    icon: AlertCircle,
    label: "MANUAL EXPORT",
  },
  unknown_cost_blocked: {
    color: "text-orange-400",
    bg: "bg-orange-500/20",
    border: "border-orange-500/30",
    icon: Lock,
    label: "UNKNOWN COST",
  },
  paid_blocked: {
    color: "text-red-400",
    bg: "bg-red-500/20",
    border: "border-red-500/30",
    icon: Lock,
    label: "PAID - BLOCKED",
  },
};

const DEFAULT_CONFIG = COST_CLASS_CONFIG.unknown_cost_blocked;

export default function ConnectorCard({ connector }) {
  const config = COST_CLASS_CONFIG[connector.cost_class] || DEFAULT_CONFIG;
  const Icon = config.icon;

  return (
    <div className={`enterprise-card border ${config.border}`} data-testid={`connector-${connector.id}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="text-white font-semibold mb-1">{connector.name}</h4>
          <span className={`px-2 py-1 rounded text-xs font-bold ${config.bg} ${config.color}`}>
            <Icon className="w-3 h-3 inline mr-1" />
            {config.label}
          </span>
        </div>
      </div>
      <div className="text-xs text-gray-400 space-y-1">
        <div>API: {connector.has_api ? "Yes" : "No"}</div>
        <div>Auth: {connector.api_authenticated ? "Configured" : "Missing"}</div>
        <div>Credentials: {connector.credential_status}</div>
        {connector.blocked_reason && (
          <div className="mt-2 p-2 bg-gray-900/50 rounded text-xs text-gray-300">
            <span className="font-semibold">Blocked:</span> {connector.blocked_reason}
          </div>
        )}
      </div>
    </div>
  );
}
