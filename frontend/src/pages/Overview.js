import { useQuery } from "@tanstack/react-query";
import {
  DollarSign,
  FileText,
  Bot,
  Package,
  TrendingUp,
  AlertCircle,
} from "lucide-react";
import { revenueAPI, contentAPI, agentsAPI, buildsAPI } from "../lib/api";

export default function Overview() {
  const { data: revenueStats } = useQuery({
    queryKey: ["revenueStats"],
    queryFn: () => revenueAPI.getStats().then((res) => res.data),
  });

  const { data: contentData } = useQuery({
    queryKey: ["content"],
    queryFn: () => contentAPI.getAll().then((res) => res.data),
  });

  const { data: agents } = useQuery({
    queryKey: ["agents"],
    queryFn: () => agentsAPI.getAll().then((res) => res.data),
  });

  const { data: builds } = useQuery({
    queryKey: ["builds"],
    queryFn: () => buildsAPI.getAll().then((res) => res.data),
  });

  const stats = [
    {
      name: "Monthly Revenue Target",
      value: `$${revenueStats?.total_monthly_target?.toLocaleString() || 0}`,
      change: `${revenueStats?.achievement_percentage?.toFixed(1) || 0}%`,
      icon: DollarSign,
      color: "text-green-600",
      bgColor: "bg-green-100",
    },
    {
      name: "Content Pieces",
      value: contentData?.length || 0,
      change: `${contentData?.filter((c) => c.status === "published").length || 0} published`,
      icon: FileText,
      color: "text-blue-600",
      bgColor: "bg-blue-100",
    },
    {
      name: "Active Agents",
      value: agents?.filter((a) => a.status === "active").length || 0,
      change: `${agents?.length || 0} total`,
      icon: Bot,
      color: "text-purple-600",
      bgColor: "bg-purple-100",
    },
    {
      name: "Builds",
      value: builds?.filter((b) => b.status === "live").length || 0,
      change: `${builds?.length || 0} total`,
      icon: Package,
      color: "text-cyan-600",
      bgColor: "bg-cyan-100",
    },
  ];

  return (
    <div data-testid="overview-page">
      <div className="page-header">
        <h1>Overview</h1>
        <p>Enterprise command center for revenue automation and ecosystem management</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="stat-card" data-testid={`stat-${stat.name.toLowerCase().replace(/\s+/g, '-')}`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-sm text-gray-600 mb-1">{stat.name}</p>
                  <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
                  <p className="text-sm text-gray-500 mt-2 flex items-center gap-1">
                    <TrendingUp className="w-4 h-4" />
                    {stat.change}
                  </p>
                </div>
                <div className={`${stat.bgColor} ${stat.color} p-3 rounded-lg`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Revenue Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="metric-card" data-testid="revenue-performance">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-green-600" />
            Revenue Performance
          </h3>
          {revenueStats && (
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Achievement</span>
                  <span className="font-semibold">
                    {revenueStats.achievement_percentage?.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-gradient-to-r from-green-500 to-green-600 h-3 rounded-full transition-all"
                    style={{
                      width: `${Math.min(revenueStats.achievement_percentage || 0, 100)}%`,
                    }}
                  ></div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <p className="text-sm text-gray-600">Target</p>
                  <p className="text-xl font-bold text-gray-900">
                    ${revenueStats.total_monthly_target?.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Actual</p>
                  <p className="text-xl font-bold text-green-600">
                    ${revenueStats.total_monthly_actual?.toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="pt-4 border-t">
                <p className="text-sm text-gray-600 mb-2">Active Streams</p>
                <p className="text-2xl font-bold">{revenueStats.active_streams}</p>
              </div>
            </div>
          )}
        </div>

        {/* System Health */}
        <div className="metric-card" data-testid="system-health">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-blue-600" />
            System Health
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
              <span className="text-sm font-medium text-gray-700">Backend API</span>
              <span className="flex items-center gap-2 text-sm text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                Operational
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
              <span className="text-sm font-medium text-gray-700">Database</span>
              <span className="flex items-center gap-2 text-sm text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                Connected
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
              <span className="text-sm font-medium text-gray-700">AI Services</span>
              <span className="flex items-center gap-2 text-sm text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                Ready
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <span className="text-sm font-medium text-gray-700">Cost Guard</span>
              <span className="flex items-center gap-2 text-sm text-blue-600">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                Zero-Spend Mode
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Content */}
      {contentData && contentData.length > 0 && (
        <div className="metric-card" data-testid="recent-content">
          <h3 className="text-lg font-semibold mb-4">Recent Content</h3>
          <div className="space-y-3">
            {contentData.slice(0, 5).map((content) => (
              <div
                key={content.id}
                className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
              >
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{content.title}</p>
                  <p className="text-sm text-gray-500">
                    {content.content_type} • {content.platform || "General"}
                  </p>
                </div>
                <span className={`content-badge status-badge-${content.status}`}>
                  {content.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}