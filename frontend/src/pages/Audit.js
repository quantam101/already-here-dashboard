import { useQuery } from "@tanstack/react-query";
import { Shield, Activity } from "lucide-react";
import { auditAPI } from "../lib/api";

function getEventTypeColor(eventType) {
  if (eventType.includes("created")) return "bg-green-500/15 text-green-300 border border-green-500/20";
  if (eventType.includes("updated")) return "bg-blue-500/15 text-blue-300 border border-blue-500/20";
  if (eventType.includes("deleted")) return "bg-red-500/15 text-red-300 border border-red-500/20";
  if (eventType.includes("approved")) return "bg-purple-500/15 text-purple-300 border border-purple-500/20";
  return "bg-gray-500/15 text-gray-300 border border-gray-500/20";
}

function AuditEventRow({ event }) {
  return (
    <div
      className="bg-[rgba(23,27,40,0.4)] border border-white/5 rounded-lg p-4 hover:border-green-500/20 transition-colors"
      data-testid={`event-${event.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className={`content-badge ${getEventTypeColor(event.event_type)}`}>
              {event.event_type}
            </span>
            <span className="content-badge bg-gray-500/15 text-gray-300 border border-gray-500/20">
              {event.resource_type}
            </span>
            <span
              className={`content-badge ${
                event.status === "success" ? "status-badge-active" : "status-badge-failed"
              }`}
            >
              {event.status}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Actor</p>
              <p className="font-semibold text-gray-300 truncate">{event.actor}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Action</p>
              <p className="font-semibold text-gray-300 truncate">{event.action}</p>
            </div>
            {event.resource_id && (
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Resource ID</p>
                <p className="font-mono text-xs text-gray-300 truncate">{event.resource_id}</p>
              </div>
            )}
          </div>
        </div>
        <div className="text-xs text-gray-500 text-right shrink-0">
          {new Date(event.timestamp).toLocaleString()}
        </div>
      </div>
    </div>
  );
}

export default function Audit() {
  const { data: events = [] } = useQuery({
    queryKey: ["auditEvents"],
    queryFn: () => auditAPI.getAll({ limit: 100 }).then((res) => res.data),
  });

  const { data: stats } = useQuery({
    queryKey: ["auditStats"],
    queryFn: () => auditAPI.getStats().then((res) => res.data),
  });

  return (
    <div data-testid="audit-page" className="p-6 dark-themed-page">
      <div className="page-header">
        <h1>Audit Log</h1>
        <p>Immutable record of all system events and actions</p>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="stat-card">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-4 h-4 text-blue-400" />
              <p className="text-xs text-gray-400 uppercase tracking-wider">Total Events</p>
            </div>
            <p className="text-3xl font-bold text-blue-400">{stats.total_events}</p>
          </div>
          {Object.entries(stats.by_event_type || {})
            .slice(0, 3)
            .map(([type, count]) => (
              <div key={type} className="stat-card">
                <p className="text-xs text-gray-400 uppercase tracking-wider mb-2 truncate">{type}</p>
                <p className="text-3xl font-bold text-green-400">{count}</p>
              </div>
            ))}
        </div>
      )}

      <div className="metric-card">
        <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
          <Activity className="w-5 h-5 text-green-400" />
          Recent Events
        </h3>
        {events.length === 0 ? (
          <div className="text-center py-12" data-testid="no-events-message">
            <Shield className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-300 mb-2">No audit events</p>
            <p className="text-sm text-gray-500">Events will appear here as actions occur</p>
          </div>
        ) : (
          <div className="space-y-3" data-testid="events-list">
            {events.map((event) => (
              <AuditEventRow key={event.id} event={event} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
