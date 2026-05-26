import { useQuery } from "@tanstack/react-query";
import { Rocket } from "lucide-react";
import { deploymentsAPI } from "../lib/api";
import DeploymentCard from "../components/DeploymentCard";

function DeploymentStats({ deployments }) {
  const stats = [
    { label: "Total", value: deployments.length, accent: "text-blue-400" },
    { label: "Success", value: deployments.filter((d) => d.status === "success").length, accent: "text-green-400" },
    { label: "Pending", value: deployments.filter((d) => d.status === "pending").length, accent: "text-yellow-400" },
    { label: "Failed", value: deployments.filter((d) => d.status === "failed").length, accent: "text-red-400" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      {stats.map((stat) => (
        <div key={stat.label} className="stat-card">
          <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">{stat.label}</p>
          <p className={`text-3xl font-bold ${stat.accent}`}>{stat.value}</p>
        </div>
      ))}
    </div>
  );
}

function DeploymentEmptyState() {
  return (
    <div className="text-center py-12" data-testid="no-deployments-message">
      <Rocket className="w-12 h-12 text-gray-500 mx-auto mb-4" />
      <p className="text-gray-300 mb-2">No deployments yet</p>
      <p className="text-sm text-gray-500">Deployments will appear here once triggered</p>
    </div>
  );
}

export default function Deployments() {
  const { data: deployments = [] } = useQuery({
    queryKey: ["deployments"],
    queryFn: () => deploymentsAPI.getAll().then((res) => res.data),
  });

  return (
    <div data-testid="deployments-page" className="p-6 dark-themed-page">
      <div className="page-header">
        <h1>Deployment Monitor</h1>
        <p>Track deployments across OCI Always Free, local laptop, and edge targets</p>
      </div>

      <DeploymentStats deployments={deployments} />

      <div className="metric-card">
        <h3 className="text-lg font-semibold text-white mb-6">Recent Deployments</h3>
        {deployments.length === 0 ? (
          <DeploymentEmptyState />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="deployments-list">
            {deployments.map((deployment) => (
              <DeploymentCard key={deployment.id} deployment={deployment} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
