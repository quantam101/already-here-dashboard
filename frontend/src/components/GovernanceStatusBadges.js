import { useQuery } from "@tanstack/react-query";
import { NavLink } from "react-router-dom";
import { ShieldAlert, AlertOctagon } from "lucide-react";
import { governanceAPI, lcacAPI } from "../lib/api";

// Compact status badges that live in the sidebar's System Status box.
// Polls /governance/approvals?status=pending and /lifelong-catch-correct/
// every 30s and renders count badges that link the operator to the right
// remediation page.

export default function GovernanceStatusBadges() {
  const { data: pendingApprovals } = useQuery({
    queryKey: ["governance", "pending-approvals"],
    queryFn: () => governanceAPI.approvals("pending").then((r) => r.data),
    refetchInterval: 30000,
  });

  const { data: lcac } = useQuery({
    queryKey: ["lcac-sidebar"],
    queryFn: () => lcacAPI.scan().then((r) => r.data),
    refetchInterval: 30000,
  });

  const approvals = Array.isArray(pendingApprovals) ? pendingApprovals : [];
  const approvalCount = approvals.length;
  // Dual-actor approvals waiting on a second signer — surface separately
  const dualActorPending = approvals.filter(
    (a) => (a.required_decisions || 1) >= 2 && (a.decisions || []).length >= 1,
  ).length;

  const findings = Array.isArray(lcac) ? lcac : lcac?.findings || [];
  const highSeverity = findings.filter((f) => f.severity === "high").length;

  if (approvalCount === 0 && highSeverity === 0) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1.5" data-testid="sidebar-governance-badges">
      {approvalCount > 0 && (
        <NavLink
          to="/approvals"
          className="flex items-center justify-between text-xs px-2 py-1.5 rounded border border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10 text-amber-300"
          data-testid="badge-pending-approvals"
        >
          <span className="flex items-center gap-1.5">
            <ShieldAlert className="w-3 h-3" />
            HITL approvals
          </span>
          <span className="font-mono font-semibold">
            {approvalCount}
            {dualActorPending > 0 && (
              <span
                className="ml-1 text-[10px] text-amber-200/70"
                title={`${dualActorPending} awaiting a SECOND distinct approver (two-person rule active)`}
              >
                · {dualActorPending} need 2nd
              </span>
            )}
          </span>
        </NavLink>
      )}
      {highSeverity > 0 && (
        <div
          className="flex items-center justify-between text-xs px-2 py-1.5 rounded border border-red-500/30 bg-red-500/5 text-red-300"
          data-testid="badge-lcac-high"
          title="High-severity Catch & Correct findings — open the floating panel for details"
        >
          <span className="flex items-center gap-1.5">
            <AlertOctagon className="w-3 h-3" />
            Catch & Correct
          </span>
          <span className="font-mono font-semibold">{highSeverity} HIGH</span>
        </div>
      )}
    </div>
  );
}
