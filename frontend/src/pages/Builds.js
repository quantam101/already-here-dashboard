import { useQuery } from "@tanstack/react-query";
import { Package, Circle } from "lucide-react";
import { buildsAPI } from "../lib/api";

function BuildCard({ build }) {
  return (
    <div
      className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-xl p-5 hover:border-green-500/30 transition-colors"
      data-testid={`build-${build.id}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <Package className="w-5 h-5 text-blue-400 shrink-0" />
            <h4 className="text-base font-semibold text-white truncate">{build.name}</h4>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`content-badge status-badge-${build.status}`}>
              <Circle className="w-2 h-2 inline mr-1 fill-current" />
              {build.status}
            </span>
            <span className="content-badge bg-purple-500/15 text-purple-300 border border-purple-500/20">
              {build.type}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm mt-4 pt-4 border-t border-white/5">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Gate Score</p>
          <p className="font-semibold text-white">{build.production_gate_score}/100</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Revenue Path</p>
          <p className="font-semibold text-white capitalize">{build.revenue_path}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Modules</p>
          <p className="font-semibold text-white">{build.modules?.length || 0}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">CI Status</p>
          <p
            className={`font-semibold ${
              build.last_ci_status === "pass" ? "text-green-400" : build.last_ci_status === "fail" ? "text-red-400" : "text-gray-400"
            }`}
          >
            {build.last_ci_status || "N/A"}
          </p>
        </div>
      </div>

      {build.next_action && (
        <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          <span className="font-semibold">Next Action:</span> {build.next_action}
        </div>
      )}
    </div>
  );
}

export default function Builds() {
  const { data: builds = [] } = useQuery({
    queryKey: ["builds"],
    queryFn: () => buildsAPI.getAll().then((res) => res.data),
  });

  const stats = [
    { label: "Total Builds", value: builds.length, accent: "text-blue-400" },
    { label: "Live", value: builds.filter((b) => b.status === "live").length, accent: "text-green-400" },
    { label: "Degraded", value: builds.filter((b) => b.status === "degraded").length, accent: "text-yellow-400" },
    { label: "Draft", value: builds.filter((b) => b.status === "draft").length, accent: "text-gray-400" },
  ];

  return (
    <div data-testid="builds-page" className="p-6 dark-themed-page">
      <div className="page-header">
        <h1>Build Registry</h1>
        <p>Track and manage all builds across the ecosystem</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => (
          <div key={stat.label} className="stat-card">
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">{stat.label}</p>
            <p className={`text-3xl font-bold ${stat.accent}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="metric-card">
        <h3 className="text-lg font-semibold text-white mb-6">Builds</h3>
        {builds.length === 0 ? (
          <div className="text-center py-12" data-testid="no-builds-message">
            <Package className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-300 mb-2">No builds registered</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="builds-list">
            {builds.map((build) => (
              <BuildCard key={build.id} build={build} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
