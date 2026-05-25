import { useQuery } from "@tanstack/react-query";
import { Package, Circle } from "lucide-react";
import { buildsAPI } from "../lib/api";

export default function Builds() {
  const { data: builds = [] } = useQuery({
    queryKey: ["builds"],
    queryFn: () => buildsAPI.getAll().then((res) => res.data),
  });

  const getStatusColor = (status) => {
    switch (status) {
      case "live":
        return "text-green-600 bg-green-100";
      case "degraded":
        return "text-yellow-600 bg-yellow-100";
      case "failed":
        return "text-red-600 bg-red-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  return (
    <div data-testid="builds-page">
      <div className="page-header">
        <h1>Build Registry</h1>
        <p>Track and manage all builds across the ecosystem</p>
      </div>

      {/* Build Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: "Total Builds", value: builds.length },
          { label: "Live", value: builds.filter((b) => b.status === "live").length },
          { label: "Degraded", value: builds.filter((b) => b.status === "degraded").length },
          { label: "Draft", value: builds.filter((b) => b.status === "draft").length },
        ].map((stat) => (
          <div key={stat.label} className="stat-card">
            <p className="text-sm text-gray-600 mb-1">{stat.label}</p>
            <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Builds List */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold mb-6">Builds</h3>
        {builds.length === 0 ? (
          <div className="text-center py-12" data-testid="no-builds-message">
            <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No builds registered</p>
            <p className="text-sm text-gray-500">Builds will appear here once created</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="builds-list">
            {builds.map((build) => (
              <div
                key={build.id}
                className="p-5 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                data-testid={`build-${build.id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <Package className="w-6 h-6 text-blue-600" />
                      <h4 className="text-lg font-semibold text-gray-900">{build.name}</h4>
                      <span className={`content-badge ${getStatusColor(build.status)}`}>
                        <Circle className="w-2 h-2 inline mr-1 fill-current" />
                        {build.status}
                      </span>
                      <span className="content-badge bg-purple-100 text-purple-700">
                        {build.type}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm mt-4">
                      <div>
                        <p className="text-gray-500">Gate Score</p>
                        <p className="font-semibold text-gray-900">
                          {build.production_gate_score}/100
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Revenue Path</p>
                        <p className="font-semibold text-gray-900">{build.revenue_path}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Modules</p>
                        <p className="font-semibold text-gray-900">{build.modules.length}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">CI Status</p>
                        <p
                          className={`font-semibold ${
                            build.last_ci_status === "pass"
                              ? "text-green-600"
                              : "text-red-600"
                          }`}
                        >
                          {build.last_ci_status || "N/A"}
                        </p>
                      </div>
                    </div>
                    {build.next_action && (
                      <div className="mt-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
                        <span className="font-semibold">Next Action:</span> {build.next_action}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}