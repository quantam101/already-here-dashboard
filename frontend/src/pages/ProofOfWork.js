import { useQuery } from "@tanstack/react-query";
import { ExternalLink, FileText, Send, Trophy } from "lucide-react";
import { ledgerAPI, publishingAPI, revenueAPI } from "../lib/api";
import ProfitMeter from "../components/ProfitMeter";
import RecordEarningsDialog from "../components/RecordEarningsDialog";
import LogPostDialog from "../components/LogPostDialog";

function LedgerRow({ entry, streamName }) {
  return (
    <tr
      className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
      data-testid={`ledger-row-${entry.id}`}
    >
      <td className="py-3 px-4 text-xs text-gray-400 font-mono whitespace-nowrap">
        {entry.occurred_on}
      </td>
      <td className="py-3 px-4 text-sm text-white">{streamName || entry.stream_id}</td>
      <td className="py-3 px-4 text-right">
        <span className="text-gray-300">${entry.gross_amount?.toLocaleString()}</span>
      </td>
      <td className="py-3 px-4 text-right">
        <span className="text-green-400 font-semibold">
          ${entry.net_amount?.toLocaleString()}
        </span>
      </td>
      <td className="py-3 px-4">
        <span className="content-badge bg-gray-500/15 text-gray-300 border border-gray-500/20">
          {entry.source}
        </span>
      </td>
      <td className="py-3 px-4">
        {entry.proof_url ? (
          <a
            href={entry.proof_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:underline inline-flex items-center gap-1 text-xs"
          >
            proof <ExternalLink className="w-3 h-3" />
          </a>
        ) : (
          <span className="text-gray-600 text-xs">—</span>
        )}
      </td>
    </tr>
  );
}

function PublishingRow({ record, streamName }) {
  return (
    <tr
      className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
      data-testid={`publishing-row-${record.id}`}
    >
      <td className="py-3 px-4 text-xs text-gray-400 font-mono whitespace-nowrap">
        {new Date(record.created_at).toLocaleDateString()}
      </td>
      <td className="py-3 px-4 text-sm text-white max-w-xs truncate">{record.title}</td>
      <td className="py-3 px-4 text-sm text-gray-300">{streamName || record.stream_id}</td>
      <td className="py-3 px-4">
        <span className="content-badge bg-purple-500/15 text-purple-300 border border-purple-500/20">
          {record.platform}
        </span>
      </td>
      <td className="py-3 px-4">
        <span className={`content-badge status-badge-${record.status === "verified" || record.status === "posted" ? "active" : record.status === "drafted" ? "draft" : "pending"}`}>
          {record.status}
        </span>
      </td>
      <td className="py-3 px-4">
        {record.post_url ? (
          <a
            href={record.post_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:underline inline-flex items-center gap-1 text-xs"
          >
            open <ExternalLink className="w-3 h-3" />
          </a>
        ) : (
          <span className="text-gray-600 text-xs">—</span>
        )}
      </td>
    </tr>
  );
}

export default function ProofOfWork() {
  const { data: progress } = useQuery({
    queryKey: ["ledgerProgress"],
    queryFn: () => ledgerAPI.progress().then((r) => r.data),
  });
  const { data: entries = [] } = useQuery({
    queryKey: ["ledger"],
    queryFn: () => ledgerAPI.getAll({ limit: 200 }).then((r) => r.data),
  });
  const { data: publishing = [] } = useQuery({
    queryKey: ["publishing"],
    queryFn: () => publishingAPI.getAll({ limit: 200 }).then((r) => r.data),
  });
  const { data: pubStats } = useQuery({
    queryKey: ["publishingStats"],
    queryFn: () => publishingAPI.stats().then((r) => r.data),
  });
  const { data: streams = [] } = useQuery({
    queryKey: ["revenueStreams"],
    queryFn: () => revenueAPI.getAll().then((r) => r.data),
  });

  const streamNameById = Object.fromEntries(streams.map((s) => [s.id, s.name]));

  const verifiedCount = pubStats?.by_status?.verified || 0;
  const postedCount = pubStats?.by_status?.posted || 0;
  const totalPosts = pubStats?.total || 0;

  return (
    <div data-testid="proof-of-work-page" className="p-6 dark-themed-page space-y-6">
      <div className="page-header flex items-center justify-between gap-4">
        <div>
          <h1>Proof of Work</h1>
          <p>Immutable ledger of real earnings + publishing log. Unlock commercialization at $25K.</p>
        </div>
        <div className="flex gap-2">
          <LogPostDialog />
          <RecordEarningsDialog />
        </div>
      </div>

      <ProfitMeter progress={progress} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center gap-2 mb-2">
            <Trophy className="w-4 h-4 text-yellow-400" />
            <p className="text-xs text-gray-400 uppercase tracking-wider">Ledger Entries</p>
          </div>
          <p className="text-3xl font-bold text-yellow-400">{progress?.entry_count || 0}</p>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-2 mb-2">
            <Send className="w-4 h-4 text-blue-400" />
            <p className="text-xs text-gray-400 uppercase tracking-wider">Total Posts</p>
          </div>
          <p className="text-3xl font-bold text-blue-400">{totalPosts}</p>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-green-400" />
            <p className="text-xs text-gray-400 uppercase tracking-wider">Posted</p>
          </div>
          <p className="text-3xl font-bold text-green-400">{postedCount}</p>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-purple-400" />
            <p className="text-xs text-gray-400 uppercase tracking-wider">Verified</p>
          </div>
          <p className="text-3xl font-bold text-purple-400">{verifiedCount}</p>
        </div>
      </div>

      <div className="enterprise-card" data-testid="ledger-table">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Revenue Ledger</h3>
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
            {entries.length} ENTRIES
          </span>
        </div>
        {entries.length === 0 ? (
          <div className="text-center py-12">
            <Trophy className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-300 mb-2">No earnings recorded yet</p>
            <p className="text-sm text-gray-500 mb-4">
              Click <span className="text-green-400 font-medium">Record Earnings</span> after you
              earn real money from any stream — even $1 is proof of work.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Date</th>
                  <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Stream</th>
                  <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Gross</th>
                  <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Net</th>
                  <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Source</th>
                  <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Proof</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <LedgerRow key={entry.id} entry={entry} streamName={streamNameById[entry.stream_id]} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="enterprise-card" data-testid="publishing-table">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Publishing Log</h3>
          <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-xs font-medium">
            {publishing.length} POSTS
          </span>
        </div>
        {publishing.length === 0 ? (
          <div className="text-center py-12">
            <Send className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-300 mb-2">No posts logged yet</p>
            <p className="text-sm text-gray-500">
              Click <span className="text-blue-400 font-medium">Log Post</span> after publishing
              anything to any platform — manual or automated.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Date</th>
                  <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Title</th>
                  <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Stream</th>
                  <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Platform</th>
                  <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">Status</th>
                  <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase tracking-wider">URL</th>
                </tr>
              </thead>
              <tbody>
                {publishing.map((record) => (
                  <PublishingRow key={record.id} record={record} streamName={streamNameById[record.stream_id]} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
