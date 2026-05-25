import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { DollarSign, Plus, TrendingUp, Edit2, Trash2 } from "lucide-react";
import { revenueAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

export default function Revenue() {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    type: "affiliate",
    monthly_target: 0,
    description: "",
  });

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
      setFormData({ name: "", type: "affiliate", monthly_target: 0, description: "" });
    },
    onError: (error) => {
      toast.error(`Failed to create revenue stream: ${error.message}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: revenueAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(["revenueStreams"]);
      queryClient.invalidateQueries(["revenueStats"]);
      toast.success("Revenue stream deleted");
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "monthly_target" ? parseFloat(value) || 0 : value,
    }));
  };

  return (
    <div data-testid="revenue-page">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1>Revenue Automation</h1>
          <p>Manage revenue streams, track performance, and automate income generation</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="flex items-center gap-2" data-testid="create-revenue-btn">
              <Plus className="w-4 h-4" />
              New Stream
            </Button>
          </DialogTrigger>
          <DialogContent data-testid="create-revenue-dialog">
            <DialogHeader>
              <DialogTitle>Create Revenue Stream</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name">Stream Name</Label>
                <Input
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="e.g., Affiliate Marketing"
                  required
                  data-testid="revenue-name-input"
                />
              </div>
              <div>
                <Label htmlFor="type">Type</Label>
                <Select
                  value={formData.type}
                  onValueChange={(value) => setFormData((prev) => ({ ...prev, type: value }))}
                >
                  <SelectTrigger data-testid="revenue-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="affiliate">Affiliate</SelectItem>
                    <SelectItem value="service">Service</SelectItem>
                    <SelectItem value="content">Content</SelectItem>
                    <SelectItem value="proposal">Proposal</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="monthly_target">Monthly Target ($)</Label>
                <Input
                  id="monthly_target"
                  name="monthly_target"
                  type="number"
                  value={formData.monthly_target}
                  onChange={handleInputChange}
                  placeholder="0"
                  data-testid="revenue-target-input"
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  placeholder="Brief description"
                  data-testid="revenue-description-input"
                />
              </div>
              <Button type="submit" className="w-full" data-testid="submit-revenue-btn">
                Create Stream
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Revenue Stats */}
      {revenueStats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="stat-card" data-testid="total-target-stat">
            <div className="flex items-center gap-3 mb-2">
              <div className="bg-green-100 text-green-600 p-2 rounded-lg">
                <DollarSign className="w-5 h-5" />
              </div>
              <p className="text-sm text-gray-600">Total Monthly Target</p>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              ${revenueStats.total_monthly_target?.toLocaleString()}
            </p>
          </div>
          <div className="stat-card" data-testid="total-actual-stat">
            <div className="flex items-center gap-3 mb-2">
              <div className="bg-blue-100 text-blue-600 p-2 rounded-lg">
                <TrendingUp className="w-5 h-5" />
              </div>
              <p className="text-sm text-gray-600">Total Actual</p>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              ${revenueStats.total_monthly_actual?.toLocaleString()}
            </p>
          </div>
          <div className="stat-card" data-testid="achievement-stat">
            <div className="flex items-center gap-3 mb-2">
              <div className="bg-purple-100 text-purple-600 p-2 rounded-lg">
                <TrendingUp className="w-5 h-5" />
              </div>
              <p className="text-sm text-gray-600">Achievement</p>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {revenueStats.achievement_percentage?.toFixed(1)}%
            </p>
          </div>
        </div>
      )}

      {/* Revenue Streams List */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold mb-6">Revenue Streams</h3>
        {streams.length === 0 ? (
          <div className="text-center py-12" data-testid="no-streams-message">
            <DollarSign className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No revenue streams yet</p>
            <p className="text-sm text-gray-500">Create your first revenue stream to start tracking</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="streams-list">
            {streams.map((stream) => (
              <div
                key={stream.id}
                className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                data-testid={`stream-${stream.id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="text-lg font-semibold text-gray-900">{stream.name}</h4>
                      <span className="content-badge bg-blue-100 text-blue-700">
                        {stream.type}
                      </span>
                      <span
                        className={`content-badge status-badge-${stream.status}`}
                      >
                        {stream.status}
                      </span>
                    </div>
                    {stream.description && (
                      <p className="text-sm text-gray-600 mb-3">{stream.description}</p>
                    )}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Monthly Target</p>
                        <p className="text-lg font-semibold text-gray-900">
                          ${stream.monthly_target?.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Actual</p>
                        <p className="text-lg font-semibold text-green-600">
                          ${stream.monthly_actual?.toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      data-testid={`edit-stream-${stream.id}`}
                    >
                      <Edit2 className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => deleteMutation.mutate(stream.id)}
                      data-testid={`delete-stream-${stream.id}`}
                    >
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </Button>
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