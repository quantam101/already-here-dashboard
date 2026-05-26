import { useQuery } from "@tanstack/react-query";
import { Bot, Activity, CheckCircle, AlertCircle } from "lucide-react";
import { agentsAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

function AgentCard({ agent, onExecute }) {
  const successes = agent.success_count || 0;
  const failures = agent.failure_count || 0;
  const total = successes + failures;
  const successRate = total > 0 ? Math.round((successes / total) * 100) : 100;
  const isHealthy = successRate >= 90;

  return (
    <div
      className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-xl p-5 hover:border-green-500/30 transition-colors"
      data-testid={`agent-${agent.id}`}
    >
      <div className="flex items-start justify-between mb-4 gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <Bot className="w-5 h-5 text-purple-400 shrink-0" />
            <h4 className="text-base font-semibold text-white truncate">{agent.name}</h4>
          </div>
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className={`content-badge status-badge-${agent.status}`}>{agent.status}</span>
            <span className="content-badge bg-blue-500/15 text-blue-300 border border-blue-500/20">
              {agent.type}
            </span>
          </div>
          <p className="text-sm text-gray-400 mb-4 line-clamp-2">{agent.mission}</p>
        </div>
        <Button
          onClick={() => onExecute(agent.id)}
          size="sm"
          className="bg-green-600 hover:bg-green-700 text-white shrink-0"
          data-testid={`execute-agent-${agent.id}`}
        >
          <Activity className="w-4 h-4 mr-1.5" />
          Execute
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-3 pt-3 border-t border-white/5">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Runs</p>
          <p className="text-base font-semibold text-white">{agent.run_count || 0}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Success rate</p>
          <p className={`text-base font-semibold flex items-center gap-1 ${isHealthy ? "text-green-400" : "text-yellow-400"}`}>
            {isHealthy ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
            {successRate}%
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">{failures > 0 ? "Recent fails" : "Status"}</p>
          {failures > 0 ? (
            <p className="text-base font-semibold text-gray-400">{failures}</p>
          ) : (
            <p className="text-base font-semibold text-green-400 flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" />
              Clean
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Agents() {
  const { data: agents = [], refetch } = useQuery({
    queryKey: ["agents"],
    queryFn: () => agentsAPI.getAll().then((res) => res.data),
  });

  const handleExecute = async (agentId) => {
    try {
      const res = await agentsAPI.execute(agentId);
      const agent = agents.find((a) => a.id === agentId);
      toast.success(`${agent?.name || agentId} run logged — see /audit for details`, {
        description: res.data?.message || "Agent run recorded",
      });
      refetch();
    } catch (error) {
      toast.error(`Failed to execute agent: ${error.message}`);
    }
  };

  const totalSuccesses = agents.reduce((sum, a) => sum + (a.success_count || 0), 0);
  const totalFails = agents.reduce((sum, a) => sum + (a.failure_count || 0), 0);
  const totalRuns = totalSuccesses + totalFails;
  const overallRate = totalRuns > 0 ? Math.round((totalSuccesses / totalRuns) * 100) : 100;

  const stats = [
    { label: "Total Agents", value: agents.length, accent: "text-blue-400" },
    { label: "Active", value: agents.filter((a) => a.status === "active").length, accent: "text-green-400" },
    { label: "Total Runs", value: agents.reduce((sum, a) => sum + (a.run_count || 0), 0), accent: "text-purple-400" },
    { label: "Fleet Success Rate", value: `${overallRate}%`, accent: overallRate >= 90 ? "text-green-400" : "text-yellow-400" },
  ];

  return (
    <div data-testid="agents-page" className="p-6 dark-themed-page">
      <div className="page-header">
        <h1>Agent Command Center</h1>
        <p>Manage and monitor {agents.length} autonomous agents · Fleet {overallRate}% success across {totalRuns.toLocaleString()} historical runs</p>
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
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white">Agent Fleet</h3>
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
            {agents.length} AGENTS
          </span>
        </div>
        {agents.length === 0 ? (
          <div className="text-center py-12" data-testid="no-agents-message">
            <Bot className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-300 mb-2">No agents configured</p>
            <p className="text-sm text-gray-500">Agents will appear here once created</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="agents-list">
            {agents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} onExecute={handleExecute} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
