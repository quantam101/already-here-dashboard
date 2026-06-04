import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL || "";

async function fetchQueue() {
  const res = await fetch(`${API}/api/work-orders/queue`);
  if (!res.ok) throw new Error("Failed to load work orders");
  return res.json();
}

async function scoreWO(payload) {
  const res = await fetch(`${API}/api/work-orders/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Score request failed");
  return res.json();
}

async function generateCounteroffer(work_order_id) {
  const res = await fetch(`${API}/api/work-orders/counteroffer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ work_order_id }),
  });
  if (!res.ok) throw new Error("Counteroffer generation failed");
  return res.json();
}

function ScoreBadge({ score }) {
  const color =
    score >= 80
      ? "bg-green-100 text-green-800"
      : score >= 50
      ? "bg-yellow-100 text-yellow-800"
      : "bg-red-100 text-red-800";
  const label =
    score >= 80 ? "Strong Match" : score >= 50 ? "Counteroffer" : "Avoid";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${color}`}>
      {score} — {label}
    </span>
  );
}

function CounterOfferModal({ text, onClose }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
        <h2 className="text-lg font-bold text-gray-900">Counteroffer Draft</h2>
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs text-yellow-800 font-medium">
          Approval required — this has NOT been sent
        </div>
        <textarea
          className="w-full border border-gray-200 rounded p-3 text-sm text-gray-800 min-h-[120px]"
          defaultValue={text}
          readOnly
        />
        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded bg-gray-100 hover:bg-gray-200 text-gray-700"
          >
            Close
          </button>
          <button
            disabled
            title="Approval required before sending"
            className="px-4 py-2 text-sm rounded bg-blue-100 text-blue-400 cursor-not-allowed"
          >
            Send (Requires Approval)
          </button>
        </div>
      </div>
    </div>
  );
}

export default function WorkOrders() {
  const qc = useQueryClient();
  const [pasteText, setPasteText] = useState("");
  const [scoreResult, setScoreResult] = useState(null);
  const [counterModal, setCounterModal] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["work-orders-queue"],
    queryFn: fetchQueue,
    refetchInterval: 30000,
  });

  const scoreMutation = useMutation({
    mutationFn: (raw_text) => scoreWO({ raw_text, source: "manual" }),
    onSuccess: (res) => {
      setScoreResult(res);
      qc.invalidateQueries(["work-orders-queue"]);
      toast.success(`Scored: ${res.score}/100 — ${res.recommendation}`);
    },
    onError: (e) => toast.error(e.message),
  });

  const counterMutation = useMutation({
    mutationFn: generateCounteroffer,
    onSuccess: (res) => setCounterModal(res.counteroffer_text),
    onError: (e) => toast.error(e.message),
  });

  const workOrders = data?.work_orders || [];

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Work Order Intelligence</h1>
        <p className="text-sm text-gray-500 mt-1">
          Score, evaluate, and manage field service work orders — Phoenix AZ, $65/hr minimum
        </p>
      </div>

      {/* Paste & Score */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3 shadow-sm">
        <h2 className="font-semibold text-gray-800">Paste Work Order</h2>
        <textarea
          className="w-full border border-gray-200 rounded p-3 text-sm text-gray-700 min-h-[100px] focus:outline-none focus:ring-2 focus:ring-blue-400"
          placeholder="Paste work order text, email body, or job description here..."
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
        />
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => scoreMutation.mutate(pasteText)}
            disabled={!pasteText.trim() || scoreMutation.isPending}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded disabled:opacity-50"
          >
            {scoreMutation.isPending ? "Scoring..." : "Score Work Order"}
          </button>
          {scoreResult && (
            <div className="flex items-center gap-2">
              <ScoreBadge score={scoreResult.score} />
              <span className="text-xs text-gray-500">
                Recommendation: <strong>{scoreResult.recommendation}</strong>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Work Order Queue */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Work Order Queue</h2>
          <span className="text-xs text-gray-500">{workOrders.length} orders</span>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Loading...</div>
        ) : workOrders.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">
            No work orders yet. Paste one above to get started.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Title</th>
                  <th className="px-4 py-3 text-left">Category</th>
                  <th className="px-4 py-3 text-left">Rate</th>
                  <th className="px-4 py-3 text-left">Score</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {workOrders.map((wo) => (
                  <tr key={wo.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 max-w-[200px]">
                      <div className="font-medium text-gray-900 truncate">{wo.title || "Untitled"}</div>
                      <div className="text-xs text-gray-400 truncate">{wo.company}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600 capitalize">{wo.category || "—"}</td>
                    <td className="px-4 py-3 text-gray-700">
                      {wo.rate_offered
                        ? `$${wo.rate_offered}${wo.rate_type === "hourly" ? "/hr" : " flat"}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <ScoreBadge score={wo.score || 0} />
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-500 capitalize">{wo.status || "pending"}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2 flex-wrap">
                        {(wo.recommendation === "counteroffer" || wo.score < 80) && (
                          <button
                            onClick={() => counterMutation.mutate(wo.id)}
                            disabled={counterMutation.isPending}
                            className="px-2 py-1 text-xs bg-yellow-100 hover:bg-yellow-200 text-yellow-800 rounded"
                          >
                            Counteroffer
                          </button>
                        )}
                        <button
                          disabled
                          title="Requires approval — cannot auto-accept"
                          className="px-2 py-1 text-xs bg-gray-100 text-gray-400 rounded cursor-not-allowed"
                        >
                          Accept*
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="p-3 border-t border-gray-100 text-xs text-gray-400">
          * Accept requires manual approval — work orders are never auto-accepted
        </div>
      </div>

      {counterModal && (
        <CounterOfferModal text={counterModal} onClose={() => setCounterModal(null)} />
      )}
    </div>
  );
}
