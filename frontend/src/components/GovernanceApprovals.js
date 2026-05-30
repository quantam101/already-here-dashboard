import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldAlert, Check, X as XIcon } from "lucide-react";
import { governanceAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

// HITL approvals managed by the governance manifest (L0-L5 + dual-actor rule).
// These are SEPARATE from the legacy `approvals` collection rendered above —
// they fire when a gated route (e.g. POST /api/proposals/draft, payments/keys/rotate)
// is called below the required autonomy bracket.

const SEVERITY_BADGE = {
  critical: "bg-red-500/15 text-red-300 border border-red-500/30",
  high: "bg-orange-500/15 text-orange-300 border border-orange-500/30",
  medium: "bg-yellow-500/15 text-yellow-300 border border-yellow-500/30",
};

function ActorField({ value, onChange }) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="your-id (alice / bob)"
      className="bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-white w-32"
      data-testid="gov-actor-input"
    />
  );
}

function GovernanceCard({ row, onDecide, actor, setActor }) {
  const dual = (row.required_decisions || 1) >= 2;
  const approvedCount = (row.decisions || []).filter((d) => d.approve).length;
  const sevClass = SEVERITY_BADGE[row.severity] || "bg-gray-500/15 text-gray-300 border border-gray-500/30";
  return (
    <div
      className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-xl p-4 hover:border-amber-500/30 transition-colors"
      data-testid={`gov-approval-${row.id}`}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="font-semibold text-white text-sm">{row.action_id}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wider ${sevClass}`}>
              {row.severity || "n/a"}
            </span>
            {dual && (
              <span
                className="text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wider bg-purple-500/15 text-purple-300 border border-purple-500/30"
                title="Two-person rule active — two distinct actors must approve"
              >
                2-OF-2 · {approvedCount}/{row.required_decisions}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 leading-snug">
            {row.context?.route || ""}
            {row.context?.title ? ` — "${row.context.title}"` : ""}
            {row.context?.platform ? ` · ${row.context.platform}` : ""}
            {row.context?.book_type ? ` · ${row.context.book_type}` : ""}
            {row.context?.doc_type ? ` · ${row.context.doc_type}` : ""}
          </p>
        </div>
        {row.status === "pending" && (
          <div className="flex items-center gap-1.5 shrink-0">
            <ActorField value={actor} onChange={setActor} />
            <Button
              onClick={() => onDecide(row.id, "approve", actor)}
              size="sm"
              className="bg-green-600 hover:bg-green-700 text-white h-7 px-2"
              data-testid={`gov-approve-${row.id}`}
              disabled={!actor.trim()}
            >
              <Check className="w-3 h-3" />
            </Button>
            <Button
              onClick={() => onDecide(row.id, "reject", actor)}
              size="sm"
              variant="destructive"
              className="h-7 px-2"
              data-testid={`gov-reject-${row.id}`}
              disabled={!actor.trim()}
            >
              <XIcon className="w-3 h-3" />
            </Button>
          </div>
        )}
      </div>
      <div className="text-[10px] text-gray-500 mt-2 pt-2 border-t border-white/5 flex flex-wrap gap-x-3 gap-y-1">
        <span>id: {row.id}</span>
        <span>requested {new Date(row.requested_at).toLocaleString()}</span>
        {(row.decisions || []).length > 0 && (
          <span>
            decisions: {row.decisions.map((d) => `${d.actor}(${d.approve ? "✓" : "✗"})`).join(", ")}
          </span>
        )}
      </div>
    </div>
  );
}

export default function GovernanceApprovals() {
  const queryClient = useQueryClient();
  const [actor, setActor] = useState("operator");

  const { data: rows = [] } = useQuery({
    queryKey: ["governance-approvals-page"],
    queryFn: () => governanceAPI.approvals().then((r) => r.data),
    refetchInterval: 20000,
  });

  const decide = useMutation({
    mutationFn: ({ id, action, actorName }) => {
      const note = `via /approvals UI by ${actorName}`;
      return action === "approve"
        ? governanceAPI.approve(id, note, actorName)
        : governanceAPI.reject(id, note, actorName);
    },
    onSuccess: (_data, vars) => {
      toast.success(`Governance ${vars.action} recorded for ${vars.id}`);
      queryClient.invalidateQueries(["governance-approvals-page"]);
      queryClient.invalidateQueries(["governance", "pending-approvals"]);
    },
    onError: (e) => toast.error(`Decision failed: ${e?.response?.data?.detail || e.message}`),
  });

  const pending = rows.filter((r) => r.status === "pending");
  const decided = rows.filter((r) => r.status !== "pending").slice(0, 8);

  return (
    <div className="metric-card mt-6" data-testid="governance-hitl-queue">
      <div className="flex items-center gap-2 mb-3">
        <ShieldAlert className="w-4 h-4 text-amber-400" />
        <h3 className="text-base font-semibold text-white">Governance HITL Queue</h3>
        <span className="text-xs text-gray-400">L0-L5 manifest · 2-of-2 dual-actor on critical gates</span>
      </div>
      <p className="text-xs text-gray-500 mb-4 leading-snug">
        Pending here means a route hit its HITL gate. Type a unique actor id (e.g. <code className="text-amber-300">alice</code>)
        before approving. Critical/L5 gates require <span className="text-purple-300">two distinct actors</span> when
        <code className="text-purple-300"> DUAL_ACTOR_APPROVAL=true</code>.
      </p>
      {rows.length === 0 ? (
        <div className="text-center py-8 text-sm text-gray-500" data-testid="gov-empty">
          No governance approvals yet. Hit any gated route below L4 to generate one.
        </div>
      ) : (
        <div className="space-y-2">
          {pending.length > 0 && (
            <>
              <p className="text-[10px] text-amber-300 uppercase tracking-wider mb-1">Pending</p>
              {pending.map((row) => (
                <GovernanceCard
                  key={row.id}
                  row={row}
                  actor={actor}
                  setActor={setActor}
                  onDecide={(id, action, a) => decide.mutate({ id, action, actorName: a })}
                />
              ))}
            </>
          )}
          {decided.length > 0 && (
            <>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mt-3 mb-1">Recent decisions</p>
              {decided.map((row) => (
                <GovernanceCard
                  key={row.id}
                  row={row}
                  actor={actor}
                  setActor={setActor}
                  onDecide={() => {}}
                />
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
