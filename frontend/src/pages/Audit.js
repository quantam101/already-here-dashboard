import { useQuery } from "@tanstack/react-query";
import { Shield, Activity } from "lucide-react";
import { auditAPI } from "../lib/api";

export default function Audit() {
  const { data: events = [] } = useQuery({
    queryKey: ["auditEvents"],
    queryFn: () => auditAPI.getAll({ limit: 100 }).then((res) => res.data),
  });

  const { data: stats } = useQuery({
    queryKey: ["auditStats"],
    queryFn: () => auditAPI.getStats().then((res) => res.data),
  });

  const getEventTypeColor = (eventType) => {
    if (eventType.includes("created")) return "bg-green-100 text-green-700";
    if (eventType.includes("updated")) return "bg-blue-100 text-blue-700";
    if (eventType.includes("deleted")) return "bg-red-100 text-red-700";
    if (eventType.includes("approved")) return "bg-purple-100 text-purple-700";
    return "bg-gray-100 text-gray-700";
  };

  return (
    <div data-testid="audit-page">
      <div className="page-header">
        <h1>Audit Log</h1>
        <p>Immutable record of all system events and actions</p>
      </div>

      {/* Audit Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="stat-card">
            <div className="flex items-center gap-3 mb-2">
              <Shield className="w-5 h-5 text-blue-600" />
              <p className="text-sm text-gray-600">Total Events</p>
            </div>
            <p className="text-3xl font-bold text-gray-900">{stats.total_events}</p>
          </div>
          {Object.entries(stats.by_event_type || {})
            .slice(0, 3)
            .map(([type, count]) => (
              <div key={type} className="stat-card">
                <p className="text-sm text-gray-600 mb-2">{type}</p>
                <p className="text-3xl font-bold text-gray-900">{count}</p>
              </div>
            ))}
        </div>
      )}

      {/* Audit Events */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Recent Events
        </h3>
        {events.length === 0 ? (
          <div className="text-center py-12" data-testid="no-events-message">
            <Shield className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No audit events</p>
            <p className="text-sm text-gray-500">Events will appear here as actions occur</p>
          </div>
        ) : (
          <div className="space-y-3" data-testid="events-list">
            {events.map((event) => (
              <div
                key={event.id}
                className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                data-testid={`event-${event.id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`content-badge ${getEventTypeColor(event.event_type)}`}>
                        {event.event_type}
                      </span>
                      <span className="content-badge bg-gray-100 text-gray-700">
                        {event.resource_type}
                      </span>
                      <span
                        className={`content-badge ${
                          event.status === "success"
                            ? "status-badge-active"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {event.status}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Actor</p>
                        <p className="font-semibold text-gray-900">{event.actor}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Action</p>
                        <p className="font-semibold text-gray-900">{event.action}</p>
                      </div>
                      {event.resource_id && (
                        <div>
                          <p className="text-gray-500">Resource ID</p>
                          <p className="font-mono text-xs text-gray-900">
                            {event.resource_id.slice(0, 8)}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 text-right">
                    {new Date(event.timestamp).toLocaleString()}
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