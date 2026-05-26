import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Radar, ExternalLink, RefreshCw, Plus, FileText, ScrollText } from "lucide-react";
import { scoutAPI, proposalsAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

const TABS = [
  { id: "viral", label: "Viral", icon: Radar, defaultQuery: "EntrepreneurRideAlong+SideProject+Entrepreneur+passive_income" },
  { id: "grants", label: "Grants", icon: ScrollText, defaultQuery: "" },
  { id: "contracts", label: "Contracts", icon: FileText, defaultQuery: "small business technology innovation" },
  { id: "news", label: "News", icon: Radar, defaultQuery: "AI automation startup" },
];

function OpportunityRow({ opp, onDraft }) {
  return (
    <div
      className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-xl p-4 hover:border-green-500/30 transition-colors"
      data-testid={`scout-opp-${opp.id}`}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-white mb-1 line-clamp-2">{opp.title}</h4>
          <div className="flex flex-wrap items-center gap-2">
            <span className="content-badge bg-blue-500/15 text-blue-300 border border-blue-500/20">
              {opp.source}
            </span>
            <span className={`content-badge ${opp.kind === "grant" ? "status-badge-active" : opp.kind === "contract" ? "bg-purple-500/15 text-purple-300 border border-purple-500/20" : "bg-yellow-500/15 text-yellow-300 border border-yellow-500/20"}`}>
              {opp.kind}
            </span>
            {typeof opp.score === "number" && opp.score > 0 && (
              <span className="text-xs text-gray-500">score {Math.round(opp.score)}</span>
            )}
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          {opp.url && (
            <a
              href={opp.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 text-xs inline-flex items-center gap-1"
              data-testid={`scout-link-${opp.id}`}
            >
              open <ExternalLink className="w-3 h-3" />
            </a>
          )}
          {(opp.kind === "grant" || opp.kind === "contract") && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onDraft(opp)}
              className="border-green-500/30 text-green-300 hover:bg-green-500/10 text-xs h-7"
              data-testid={`scout-draft-${opp.id}`}
            >
              <Plus className="w-3 h-3 mr-1" /> Draft
            </Button>
          )}
        </div>
      </div>
      {opp.summary && (
        <p className="text-xs text-gray-400 line-clamp-2 mt-2">{opp.summary}</p>
      )}
    </div>
  );
}

export default function Scout() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("viral");
  const [queries, setQueries] = useState(() =>
    Object.fromEntries(TABS.map((t) => [t.id, t.defaultQuery]))
  );

  const { data: opps = [], isFetching, refetch } = useQuery({
    queryKey: ["scout", activeTab, queries[activeTab]],
    queryFn: () => {
      const params =
        activeTab === "viral" ? { subreddits: queries.viral } :
        activeTab === "news" ? { query: queries.news } :
        activeTab === "contracts" ? { keywords: queries.contracts } : {};
      return scoutAPI[activeTab](params).then((r) => r.data);
    },
    staleTime: 60_000,
  });

  const draftMutation = useMutation({
    mutationFn: (payload) => proposalsAPI.draft(payload),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["proposals"] });
      toast.success(`Drafted: ${res.data?.title || "document"}`);
    },
    onError: (err) => {
      const detail = err?.response?.data?.detail || err.message;
      toast.error(`Draft failed: ${detail}`);
    },
  });

  const handleDraft = (opp) => {
    const docType = opp.kind === "grant" ? "grant_proposal" : "contract_proposal";
    draftMutation.mutate({
      doc_type: docType,
      title: opp.title.slice(0, 200),
      target_org: opp.metadata?.agency || opp.source,
      opportunity_url: opp.url,
      requirements: [opp.summary || "See opportunity URL"].filter(Boolean),
      evidence: [
        "H&M RFID US0275 - 55 readers, 61 data runs, 4 new APs successfully deployed",
        "Already Here Command OS - $0/month governed AI operating system with 10 revenue streams",
      ],
      company_profile: { name: "Already Here", naics: "541512" },
    });
  };

  return (
    <div data-testid="scout-page" className="p-6 dark-themed-page space-y-6">
      <div className="page-header flex items-center justify-between gap-4">
        <div>
          <h1>Scout</h1>
          <p>Free viral content + grant + contract discovery. All sources $0/month.</p>
        </div>
        <Button
          onClick={() => refetch()}
          disabled={isFetching}
          variant="outline"
          className="border-green-500/30 text-green-300 hover:bg-green-500/10"
          data-testid="scout-refresh"
        >
          <RefreshCw className={`w-4 h-4 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
          {isFetching ? "Scanning..." : "Refresh"}
        </Button>
      </div>

      <div className="flex flex-wrap gap-2" data-testid="scout-tabs">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors flex items-center gap-2 ${
                isActive
                  ? "bg-green-500/15 border-green-500/30 text-green-300"
                  : "bg-transparent border-white/10 text-gray-400 hover:border-white/20 hover:text-white"
              }`}
              data-testid={`scout-tab-${tab.id}`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {(activeTab === "viral" || activeTab === "news" || activeTab === "contracts") && (
        <div className="enterprise-card">
          <label className="text-xs text-gray-400 uppercase tracking-wider mb-2 block">
            {activeTab === "viral" && "Subreddits (separated by +)"}
            {activeTab === "news" && "Search query"}
            {activeTab === "contracts" && "Keywords"}
          </label>
          <Input
            value={queries[activeTab]}
            onChange={(e) => setQueries({ ...queries, [activeTab]: e.target.value })}
            className="bg-[#171b28] border-white/10 text-white"
            data-testid={`scout-input-${activeTab}`}
          />
        </div>
      )}

      <div className="enterprise-card" data-testid="scout-results">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white capitalize">{activeTab} Opportunities</h3>
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
            {opps.length} found · $0 cost
          </span>
        </div>
        {opps.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            {isFetching ? "Scanning free sources..." : "No results - try refreshing or different keywords"}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {opps.map((opp) => (
              <OpportunityRow key={opp.id} opp={opp} onDraft={handleDraft} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
