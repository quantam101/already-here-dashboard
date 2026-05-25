import { useQuery } from "@tanstack/react-query";
import { Bot, Activity, CheckCircle, XCircle } from "lucide-react";
import { agentsAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function Agents() {
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: () => agentsAPI.getAll().then((res) => res.data),
  });

  const handleExecute = async (agentId) => {
    try {
      await agentsAPI.execute(agentId);
      toast.success("Agent execution started");
    } catch (error) {
      toast.error(`Failed to execute agent: ${error.message}`);
    }
  };

  return (
    <div data-testid="agents-page">
      <div className="page-header">
        <h1>Agent Command Center</h1>
        <p>Manage and monitor autonomous agents across the ecosystem</p>
      </div>

      {/* Agent Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
          {
            label: "Total Agents",
            value: agents.length,
            color: "bg-blue-100 text-blue-600",
          },
          {
            label: "Active",
            value: agents.filter((a) => a.status === "active").length,
            color: "bg-green-100 text-green-600",
          },
          {
            label: "Total Runs",
            value: agents.reduce((sum, a) => sum + (a.run_count || 0), 0),
            color: "bg-purple-100 text-purple-600",
          },
          {
            label: "Success Rate",
            value: agents.reduce((sum, a) => sum + (a.success_count || 0), 0),
            color: "bg-cyan-100 text-cyan-600",
          },
        ].map((stat) => (
          <div key={stat.label} className="stat-card">
            <p className="text-sm text-gray-600 mb-1">{stat.label}</p>
            <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Agents List */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold mb-6">Agents</h3>
        {agents.length === 0 ? (
          <div className="text-center py-12" data-testid="no-agents-message">
            <Bot className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No agents configured</p>
            <p className="text-sm text-gray-500">Agents will appear here once created</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="agents-list">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className="p-5 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                data-testid={`agent-${agent.id}`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <Bot className="w-6 h-6 text-purple-600" />
                      <h4 className="text-lg font-semibold text-gray-900">{agent.name}</h4>
                      <span
                        className={`content-badge ${agent.status === "active" ? "status-badge-active" : "bg-gray-100 text-gray-600"}`}
                      >
                        {agent.status}
                      </span>
                      <span className="content-badge bg-blue-100 text-blue-700">
                        {agent.type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-3">{agent.mission}</p>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Run Count</p>
                        <p className="font-semibold text-gray-900">{agent.run_count || 0}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Success</p>
                        <p className="font-semibold text-green-600 flex items-center gap-1">
                          <CheckCircle className="w-4 h-4" />
                          {agent.success_count || 0}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Failures</p>
                        <p className="font-semibold text-red-600 flex items-center gap-1">
                          <XCircle className="w-4 h-4" />
                          {agent.failure_count || 0}
                        </p>
                      </div>
                    </div>
                  </div>
                  <Button
                    onClick={() => handleExecute(agent.id)}
                    className="flex items-center gap-2"
                    data-testid={`execute-agent-${agent.id}`}
                  >
                    <Activity className="w-4 h-4" />
                    Execute
                  </Button>
                </div>
                {agent.last_run && (
                  <div className="text-xs text-gray-500 border-t pt-3">
                    Last run: {new Date(agent.last_run).toLocaleString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}