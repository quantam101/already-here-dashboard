import { Circle } from "lucide-react";

const STATUS_COLORS = {
  success: "text-green-600 bg-green-100",
  pending: "text-yellow-600 bg-yellow-100",
  failed: "text-red-600 bg-red-100",
};
const DEFAULT_STATUS_COLOR = "text-gray-600 bg-gray-100";

function getStatusColor(status) {
  return STATUS_COLORS[status] || DEFAULT_STATUS_COLOR;
}

function DeploymentHeader({ deployment }) {
  return (
    <div className="flex items-center gap-3 mb-3">
      <span className={`content-badge ${getStatusColor(deployment.status)}`}>
        <Circle className="w-2 h-2 inline mr-1 fill-current" />
        {deployment.status}
      </span>
      <span className="content-badge bg-blue-100 text-blue-700">{deployment.environment}</span>
      <span className="content-badge bg-purple-100 text-purple-700">{deployment.target}</span>
    </div>
  );
}

function DeploymentMeta({ deployment }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
      <div>
        <p className="text-gray-500">Build ID</p>
        <p className="font-mono text-xs text-gray-900">{deployment.build_id.slice(0, 8)}</p>
      </div>
      <div>
        <p className="text-gray-500">Version</p>
        <p className="font-semibold text-gray-900">{deployment.version}</p>
      </div>
      <div>
        <p className="text-gray-500">Deployed By</p>
        <p className="font-semibold text-gray-900">{deployment.deployed_by}</p>
      </div>
      <div>
        <p className="text-gray-500">Rollback</p>
        <p className={`font-semibold ${deployment.rollback_available ? "text-green-600" : "text-gray-400"}`}>
          {deployment.rollback_available ? "Available" : "N/A"}
        </p>
      </div>
    </div>
  );
}

export default function DeploymentCard({ deployment }) {
  return (
    <div
      className="p-5 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
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
            className="text-blue-600 hover:underline"
          >
            {deployment.health_check_url}
          </a>
        </div>
      )}
      {deployment.error_log && (
        <div className="mt-3 p-3 bg-red-50 rounded-lg text-sm text-red-800">
          <span className="font-semibold">Error:</span> {deployment.error_log}
        </div>
      )}
      <div className="text-xs text-gray-500 mt-3 border-t pt-3">
        Deployed {new Date(deployment.created_at).toLocaleString()}
      </div>
    </div>
  );
}
