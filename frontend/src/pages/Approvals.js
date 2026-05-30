import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock, AlertTriangle } from "lucide-react";
import { approvalsAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import GovernanceApprovals from "../components/GovernanceApprovals";

const PRIORITY_COLORS = {
  critical: "bg-red-500/15 text-red-300 border border-red-500/20",
  high: "bg-orange-500/15 text-orange-300 border border-orange-500/20",
  medium: "bg-yellow-500/15 text-yellow-300 border border-yellow-500/20",
};
const DEFAULT_PRIORITY_COLOR = "bg-gray-500/15 text-gray-300 border border-gray-500/20";

const STATUS_BADGE_CLASSES = {
  pending: "status-badge-pending",
  approved: "status-badge-active",
  rejected: "status-badge-failed",
};

function getPriorityColor(priority) {
  return PRIORITY_COLORS[priority] || DEFAULT_PRIORITY_COLOR;
}

function getStatusBadgeClass(status) {
  return STATUS_BADGE_CLASSES[status] || "status-badge-failed";
}

function ApprovalStats({ approvals, pendingCount }) {
  const stats = [
    { label: "Pending", value: pendingCount, icon: Clock, accent: "text-yellow-400" },
    { label: "Approved", value: approvals.filter((a) => a.status === "approved").length, icon: CheckCircle2, accent: "text-green-400" },
    { label: "Rejected", value: approvals.filter((a) => a.status === "rejected").length, icon: AlertTriangle, accent: "text-red-400" },
    { label: "Total", value: approvals.length, icon: CheckCircle2, accent: "text-blue-400" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <div key={stat.label} className="stat-card">
            <div className="flex items-center gap-2 mb-2">
              <Icon className={`w-4 h-4 ${stat.accent}`} />
              <p className="text-xs text-gray-400 uppercase tracking-wider">{stat.label}</p>
            </div>
            <p className={`text-3xl font-bold ${stat.accent}`}>{stat.value}</p>
          </div>
        );
      })}
    </div>
  );
}

function ApprovalActions({ approvalId, onDecide }) {
  return (
    <div className="flex gap-2 shrink-0">
      <Button
        onClick={() => onDecide(approvalId, "approved")}
        size="sm"
        className="bg-green-600 hover:bg-green-700 text-white"
        data-testid={`approve-${approvalId}`}
      >
        Approve
      </Button>
      <Button
        onClick={() => onDecide(approvalId, "rejected")}
        size="sm"
        variant="destructive"
        data-testid={`reject-${approvalId}`}
      >
        Reject
      </Button>
    </div>
  );
}

function ApprovalCard({ approval, onDecide }) {
  return (
    <div
      className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-xl p-5 hover:border-green-500/30 transition-colors"
      data-testid={`approval-${approval.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <h4 className="text-base font-semibold text-white">{approval.action}</h4>
            <span className={`content-badge ${getPriorityColor(approval.priority)}`}>
              {approval.priority}
            </span>
            <span className={`content-badge ${getStatusBadgeClass(approval.status)}`}>
              {approval.status}
            </span>
          </div>
          <p className="text-sm text-gray-400 mb-3">{approval.reason}</p>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Resource</p>
              <p className="font-semibold text-gray-300">{approval.resource_type}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Requested By</p>
              <p className="font-semibold text-gray-300">{approval.requested_by}</p>
            </div>
            {approval.approved_by && (
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Approved By</p>
                <p className="font-semibold text-gray-300">{approval.approved_by}</p>
              </div>
            )}
          </div>
        </div>
        {approval.status === "pending" && (
          <ApprovalActions approvalId={approval.id} onDecide={onDecide} />
        )}
      </div>
      <div className="text-xs text-gray-500 mt-3 pt-3 border-t border-white/5">
        Requested {new Date(approval.created_at).toLocaleString()}
      </div>
    </div>
  );
}

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
        variables.decision.status === "approved" ? "Request approved" : "Request rejected"
      );
    },
    onError: (error) => toast.error(`Failed to process approval: ${error.message}`),
  });

  const handleDecision = (id, status) => {
    decideMutation.mutate({ id, decision: { status, approved_by: "user" } });
  };

  const pendingApprovals = approvals.filter((a) => a.status === "pending");

  return (
    <div data-testid="approvals-page" className="p-6 dark-themed-page">
      <div className="page-header">
        <h1>Approval Queue</h1>
        <p>Review and approve actions requiring human oversight</p>
      </div>

      <ApprovalStats approvals={approvals} pendingCount={pendingApprovals.length} />

      <div className="metric-card">
        <h3 className="text-lg font-semibold text-white mb-6">Approval Requests</h3>
        {approvals.length === 0 ? (
          <div className="text-center py-12" data-testid="no-approvals-message">
            <CheckCircle2 className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-300 mb-2">No approval requests</p>
            <p className="text-sm text-gray-500">Requests requiring approval will appear here</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="approvals-list">
            {approvals.map((approval) => (
              <ApprovalCard key={approval.id} approval={approval} onDecide={handleDecision} />
            ))}
          </div>
        )}
      </div>

      <GovernanceApprovals />
    </div>
  );
}
