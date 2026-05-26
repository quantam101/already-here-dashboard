import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { DollarSign, TrendingUp, Target } from "lucide-react";
import { revenueAPI } from "../lib/api";
import { toast } from "sonner";
import RevenueStreamDialog from "../components/RevenueStreamDialog";
import RevenueStreamCard from "../components/RevenueStreamCard";

const INITIAL_FORM = { name: "", type: "affiliate", monthly_target: 0, description: "" };

function RevenueStats({ stats }) {
  if (!stats) return null;
  const items = [
    {
      label: "Total Monthly Target",
      value: `$${(stats.total_monthly_target || 0).toLocaleString()}`,
      icon: Target,
      accent: "text-green-400",
      bg: "bg-green-500/10 border-green-500/20",
      testId: "total-target-stat",
    },
    {
      label: "Total Actual",
      value: `$${(stats.total_monthly_actual || 0).toLocaleString()}`,
      icon: DollarSign,
      accent: "text-blue-400",
      bg: "bg-blue-500/10 border-blue-500/20",
      testId: "total-actual-stat",
    },
    {
      label: "Achievement",
      value: `${(stats.achievement_percentage || 0).toFixed(1)}%`,
      icon: TrendingUp,
      accent: "text-purple-400",
      bg: "bg-purple-500/10 border-purple-500/20",
      testId: "achievement-stat",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      {items.map((stat) => {
        const Icon = stat.icon;
        return (
          <div key={stat.label} className="stat-card" data-testid={stat.testId}>
            <div className="flex items-center gap-3 mb-3">
              <div className={`${stat.bg} ${stat.accent} p-2 rounded-lg border`}>
                <Icon className="w-5 h-5" />
              </div>
              <p className="text-sm text-gray-400">{stat.label}</p>
            </div>
            <p className="text-3xl font-bold text-white">{stat.value}</p>
          </div>
        );
      })}
    </div>
  );
}

function StreamsList({ streams, onDelete }) {
  if (streams.length === 0) {
    return (
      <div className="text-center py-12" data-testid="no-streams-message">
        <DollarSign className="w-12 h-12 text-gray-500 mx-auto mb-4" />
        <p className="text-gray-300 mb-2">No revenue streams yet</p>
        <p className="text-sm text-gray-500">Create your first revenue stream to start tracking</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="streams-list">
      {streams.map((stream) => (
        <RevenueStreamCard key={stream.id} stream={stream} onDelete={onDelete} />
      ))}
    </div>
  );
}

export default function Revenue() {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState(INITIAL_FORM);

  const { data: revenueStats } = useQuery({
    queryKey: ["revenueStats"],
    queryFn: () => revenueAPI.getStats().then((res) => res.data),
  });

  const { data: streams = [] } = useQuery({
    queryKey: ["revenueStreams"],
    queryFn: () => revenueAPI.getAll().then((res) => res.data),
  });

  const createMutation = useMutation({
    mutationFn: revenueAPI.create,
    onSuccess: () => {
      queryClient.invalidateQueries(["revenueStreams"]);
      queryClient.invalidateQueries(["revenueStats"]);
      toast.success("Revenue stream created successfully");
      setIsDialogOpen(false);
      setFormData(INITIAL_FORM);
    },
    onError: (error) => toast.error(`Failed to create revenue stream: ${error.message}`),
  });

  const deleteMutation = useMutation({
    mutationFn: revenueAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(["revenueStreams"]);
      queryClient.invalidateQueries(["revenueStats"]);
      toast.success("Revenue stream deleted");
    },
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "monthly_target" ? parseFloat(value) || 0 : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  return (
    <div data-testid="revenue-page" className="p-6 dark-themed-page">
      <div className="page-header flex items-center justify-between gap-4">
        <div>
          <h1>Revenue Automation</h1>
          <p>Manage revenue streams, track performance, automate income generation</p>
        </div>
        <RevenueStreamDialog
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
          formData={formData}
          onChange={handleInputChange}
          onSubmit={handleSubmit}
        />
      </div>

      <RevenueStats stats={revenueStats} />

      <div className="metric-card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white">Revenue Streams</h3>
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
            {streams.length} STREAMS
          </span>
        </div>
        <StreamsList streams={streams} onDelete={deleteMutation.mutate} />
      </div>
    </div>
  );
}
