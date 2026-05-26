import { ACTIVITY_TYPES } from "../lib/chartConfig";

export default function ActivityFeed({ activities }) {
  return (
    <div className="enterprise-card" data-testid="activity-feed">
      <h3 className="text-lg font-semibold text-white mb-4">User Activity</h3>
      <div className="space-y-2">
        {activities.map((activity) => (
          <div key={activity.id} className="activity-item">
            <div className="flex items-start gap-2">
              <div className={`w-1.5 h-1.5 rounded-full mt-1.5 ${ACTIVITY_TYPES[activity.type] || ACTIVITY_TYPES.info}`} />
              <div className="flex-1">
                <p className="text-gray-300 text-sm">{activity.text}</p>
                <p className="text-gray-500 text-xs mt-1">{activity.time}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
