import { useQuery } from "@tanstack/react-query";
import { Rocket, Circle } from "lucide-react";
import { deploymentsAPI } from "../lib/api";

export default function Deployments() {
  const { data: deployments = [] } = useQuery({
    queryKey: ["deployments"],
    queryFn: () => deploymentsAPI.getAll().then((res) => res.data),
  });

  const getStatusColor = (status) => {
    switch (status) {
      case "success":
        return "text-green-600 bg-green-100";
      case "pending":
        return "text-yellow-600 bg-yellow-100";
      case "failed":
        return "text-red-600 bg-red-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  return (
    <div data-testid="deployments-page">
      <div className="page-header">
        <h1>Deployment Monitor</h1>
        <p>Track deployments across OCI, Vercel, and local environments</p>
      </div>

      {/* Deployment Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: "Total", value: deployments.length },
          {
            label: "Success",
            value: deployments.filter((d) => d.status === "success").length,
          },
          {
            label: "Pending",
            value: deployments.filter((d) => d.status === "pending").length,
          },
          { label: "Failed", value: deployments.filter((d) => d.status === "failed").length },
        ].map((stat) => (
          <div key={stat.label} className="stat-card">
            <p className="text-sm text-gray-600 mb-1">{stat.label}</p>
            <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Deployments List */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold mb-6">Recent Deployments</h3>
        {deployments.length === 0 ? (
          <div className="text-center py-12" data-testid="no-deployments-message">
            <Rocket className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No deployments yet</p>
            <p className="text-sm text-gray-500">Deployments will appear here once triggered</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="deployments-list">
            {deployments.map((deployment) => (
              <div
                key={deployment.id}
                className="p-5 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                data-testid={`deployment-${deployment.id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <Rocket className="w-5 h-5 text-blue-600" />
                      <span className={`content-badge ${getStatusColor(deployment.status)}`}>
                        <Circle className="w-2 h-2 inline mr-1 fill-current" />
                        {deployment.status}
                      </span>
                      <span className="content-badge bg-blue-100 text-blue-700">
                        {deployment.environment}
                      </span>
                      <span className="content-badge bg-purple-100 text-purple-700">
                        {deployment.target}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Build ID</p>
                        <p className="font-mono text-xs text-gray-900">
                          {deployment.build_id.slice(0, 8)}
                        </p>
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
                        <p
                          className={`font-semibold ${
                            deployment.rollback_available ? "text-green-600" : "text-gray-400"
                          }`}
                        >
                          {deployment.rollback_available ? "Available" : "N/A"}
                        </p>
                      </div>
                    </div>
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
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-3 border-t pt-3">
                  Deployed {new Date(deployment.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}