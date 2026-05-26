import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { DollarSign, TrendingUp } from "lucide-react";
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
      value: `$${stats.total_monthly_target?.toLocaleString()}`,
      icon: DollarSign,
      bg: "bg-green-100",
      color: "text-green-600",
      testId: "total-target-stat",
    },
    {
      label: "Total Actual",
      value: `$${stats.total_monthly_actual?.toLocaleString()}`,
      icon: TrendingUp,
      bg: "bg-blue-100",
      color: "text-blue-600",
      testId: "total-actual-stat",
    },
    {
      label: "Achievement",
      value: `${stats.achievement_percentage?.toFixed(1)}%`,
      icon: TrendingUp,
      bg: "bg-purple-100",
      color: "text-purple-600",
      testId: "achievement-stat",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      {items.map((stat) => {
        const Icon = stat.icon;
        return (
          <div key={stat.label} className="stat-card" data-testid={stat.testId}>
            <div className="flex items-center gap-3 mb-2">
              <div className={`${stat.bg} ${stat.color} p-2 rounded-lg`}>
                <Icon className="w-5 h-5" />
              </div>
              <p className="text-sm text-gray-600">{stat.label}</p>
            </div>
            <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
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
        <DollarSign className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600 mb-2">No revenue streams yet</p>
        <p className="text-sm text-gray-500">Create your first revenue stream to start tracking</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="streams-list">
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
    <div data-testid="revenue-page">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1>Revenue Automation</h1>
          <p>Manage revenue streams, track performance, and automate income generation</p>
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
        <h3 className="text-lg font-semibold mb-6">Revenue Streams</h3>
        <StreamsList streams={streams} onDelete={deleteMutation.mutate} />
      </div>
    </div>
  );
}
