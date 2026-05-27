import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, Info, Clock, Brain, AlertCircle } from "lucide-react";

const TYPE_CFG = {
  success:   { icon: CheckCircle, color: "#22c55e", border: "rgba(34,197,94,0.3)" },
  info:      { icon: Info,        color: "#3b82f6", border: "rgba(59,130,246,0.3)" },
  pending:   { icon: Clock,       color: "#f59e0b", border: "rgba(245,158,11,0.3)" },
  sovereign: { icon: Brain,       color: "#6366f1", border: "rgba(99,102,241,0.4)" },
  error:     { icon: AlertCircle, color: "#ef4444", border: "rgba(239,68,68,0.3)" },
};

export default function ActivityFeed({ activities = [] }) {
  return (
    <div className="enterprise-card" data-testid="activity-feed">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-white">Live Activity</h3>
        <span className="flex items-center gap-1.5 text-xs text-green-400">
          <span className="live-dot" style={{ width: 6, height: 6 }} />
          Live
        </span>
      </div>
      <div className="space-y-2">
        <AnimatePresence>
          {activities.map((a, i) => {
            const cfg = TYPE_CFG[a.type] || TYPE_CFG.info;
            const Icon = cfg.icon;
            return (
              <motion.div
                key={a.id}
                className={`activity-item ${a.type === "sovereign" ? "type-sovereign" : a.type === "error" ? "type-error" : ""}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05, duration: 0.3 }}
                style={{ borderLeftColor: cfg.border }}
              >
                <div className="flex items-start gap-2">
                  <Icon className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: cfg.color }} />
                  <div className="min-w-0">
                    <p className="text-xs text-gray-200 leading-snug">{a.text}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{a.time}</p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}