import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock, AlertTriangle } from "lucide-react";
import { approvalsAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function Approvals() {
  const queryClient = useQueryClient();

  const { data: approvals = [] } = useQuery({
    queryKey: ["approvals"],
    queryFn: () => approvalsAPI.getAll().then((res) => res.data),
  });

  const decideMutation = useMutation({
    mutationFn: ({ id, decision }) => approvalsAPI.decide(id, decision),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries(["approvals"]);
      toast.success(
        variables.decision.status === "approved"
          ? "Request approved"
          : "Request rejected"
      );
    },
    onError: (error) => {
      toast.error(`Failed to process approval: ${error.message}`);
    },
  });

  const handleDecision = (id, status) => {
    decideMutation.mutate({
      id,
      decision: {
        status,
        approved_by: "user",
      },
    });
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case "critical":
        return "text-red-600 bg-red-100";
      case "high":
        return "text-orange-600 bg-orange-100";
      case "medium":
        return "text-yellow-600 bg-yellow-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  const pendingApprovals = approvals.filter((a) => a.status === "pending");

  return (
    <div data-testid="approvals-page">
      <div className="page-header">
        <h1>Approval Queue</h1>
        <p>Review and approve actions requiring human oversight</p>
      </div>

      {/* Approval Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: "Pending", value: pendingApprovals.length, icon: Clock },
          {
            label: "Approved",
            value: approvals.filter((a) => a.status === "approved").length,
            icon: CheckCircle2,
          },
          {
            label: "Rejected",
            value: approvals.filter((a) => a.status === "rejected").length,
            icon: AlertTriangle,
          },
          { label: "Total", value: approvals.length, icon: CheckCircle2 },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="stat-card">
              <div className="flex items-center gap-3 mb-2">
                <Icon className="w-5 h-5 text-blue-600" />
                <p className="text-sm text-gray-600">{stat.label}</p>
              </div>
              <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
            </div>
          );
        })}
      </div>

      {/* Approvals List */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold mb-6">Approval Requests</h3>
        {approvals.length === 0 ? (
          <div className="text-center py-12" data-testid="no-approvals-message">
            <CheckCircle2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No approval requests</p>
            <p className="text-sm text-gray-500">
              Requests requiring approval will appear here
            </p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="approvals-list">
            {approvals.map((approval) => (
              <div
                key={approval.id}
                className="p-5 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                data-testid={`approval-${approval.id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="text-lg font-semibold text-gray-900">{approval.action}</h4>
                      <span className={`content-badge ${getPriorityColor(approval.priority)}`}>
                        {approval.priority}
                      </span>
                      <span
                        className={`content-badge ${
                          approval.status === "pending"
                            ? "status-badge-pending"
                            : approval.status === "approved"
                              ? "status-badge-active"
                              : "bg-red-100 text-red-700"
                        }`}
                      >
                        {approval.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-3">{approval.reason}</p>
                    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Resource</p>
                        <p className="font-semibold text-gray-900">
                          {approval.resource_type}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Requested By</p>
                        <p className="font-semibold text-gray-900">{approval.requested_by}</p>
                      </div>
                      {approval.approved_by && (
                        <div>
                          <p className="text-gray-500">Approved By</p>
                          <p className="font-semibold text-gray-900">{approval.approved_by}</p>
                        </div>
                      )}
                    </div>
                  </div>
                  {approval.status === "pending" && (
                    <div className="flex gap-2 ml-4">
                      <Button
                        onClick={() => handleDecision(approval.id, "approved")}
                        variant="default"
                        size="sm"
                        data-testid={`approve-${approval.id}`}
                      >
                        Approve
                      </Button>
                      <Button
                        onClick={() => handleDecision(approval.id, "rejected")}
                        variant="destructive"
                        size="sm"
                        data-testid={`reject-${approval.id}`}
                      >
                        Reject
                      </Button>
                    </div>
                  )}
                </div>
                <div className="text-xs text-gray-500 mt-3 border-t pt-3">
                  Requested {new Date(approval.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}