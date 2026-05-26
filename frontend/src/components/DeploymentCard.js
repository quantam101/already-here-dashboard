import { Circle } from "lucide-react";

function DeploymentHeader({ deployment }) {
  return (
    <div className="flex flex-wrap items-center gap-2 mb-3">
      <span className={`content-badge status-badge-${deployment.status}`}>
        <Circle className="w-2 h-2 inline mr-1 fill-current" />
        {deployment.status}
      </span>
      <span className="content-badge bg-blue-500/15 text-blue-300 border border-blue-500/20">
        {deployment.environment}
      </span>
      <span className="content-badge bg-purple-500/15 text-purple-300 border border-purple-500/20">
        {deployment.target}
      </span>
      {deployment.health_status === "healthy" && (
        <span className="content-badge bg-green-500/15 text-green-300 border border-green-500/20">
          healthy
        </span>
      )}
    </div>
  );
}

function DeploymentMeta({ deployment }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Build</p>
        <p className="font-mono text-xs text-gray-300">{deployment.build_id.slice(0, 10)}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Version</p>
        <p className="font-semibold text-white">{deployment.version}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Deployed By</p>
        <p className="font-semibold text-gray-300 truncate">{deployment.deployed_by}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Rollback</p>
        <p className={`font-semibold ${deployment.rollback_available ? "text-green-400" : "text-gray-500"}`}>
          {deployment.rollback_available ? "Available" : "N/A"}
        </p>
      </div>
    </div>
  );
}

export default function DeploymentCard({ deployment }) {
  return (
    <div
      className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-xl p-5 hover:border-green-500/30 transition-colors"
      data-testid={`deployment-${deployment.id}`}
    >
      <DeploymentHeader deployment={deployment} />
      <DeploymentMeta deployment={deployment} />
      {deployment.health_check_url && (
        <div className="mt-3 text-xs">
          <span className="text-gray-500">Health: </span>
          <a
            href={deployment.health_check_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:underline break-all"
          >
            {deployment.health_check_url}
          </a>
        </div>
      )}
      {deployment.error_log && (
        <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-300">
          <span className="font-semibold">Error:</span> {deployment.error_log}
        </div>
      )}
      <div className="text-xs text-gray-500 mt-3 pt-3 border-t border-white/5">
        Deployed {new Date(deployment.created_at).toLocaleString()}
      </div>
    </div>
  );
}
