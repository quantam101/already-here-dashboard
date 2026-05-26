import { Button } from "@/components/ui/button";
import { Edit2, Trash2 } from "lucide-react";

export default function RevenueStreamCard({ stream, onDelete }) {
  return (
    <div
      className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
      data-testid={`stream-${stream.id}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h4 className="text-lg font-semibold text-gray-900">{stream.name}</h4>
            <span className="content-badge bg-blue-100 text-blue-700">{stream.type}</span>
            <span className={`content-badge status-badge-${stream.status}`}>{stream.status}</span>
          </div>
          {stream.description && <p className="text-sm text-gray-600 mb-3">{stream.description}</p>}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 mb-1">Monthly Target</p>
              <p className="text-lg font-semibold text-gray-900">
                ${stream.monthly_target?.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Actual</p>
              <p className="text-lg font-semibold text-green-600">
                ${stream.monthly_actual?.toLocaleString()}
              </p>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" data-testid={`edit-stream-${stream.id}`}>
            <Edit2 className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onDelete(stream.id)}
            data-testid={`delete-stream-${stream.id}`}
          >
            <Trash2 className="w-4 h-4 text-red-600" />
          </Button>
        </div>
      </div>
    </div>
  );
}
