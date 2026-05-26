import { Button } from "@/components/ui/button";
import { Wand2 } from "lucide-react";

export default function IdeaCard({ idea, onGenerateScript }) {
  return (
    <div className="enterprise-card" data-testid={`idea-${idea.id}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h4 className="text-white font-semibold mb-1">{idea.title}</h4>
          <p className="text-gray-400 text-sm">{idea.description}</p>
        </div>
        <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-xs">
          {idea.status}
        </span>
      </div>
      <div className="flex flex-wrap gap-2 mb-3">
        {(idea.target_platforms || []).map((p) => (
          <span key={p} className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-xs">
            {p}
          </span>
        ))}
      </div>
      <Button
        size="sm"
        onClick={() => onGenerateScript(idea.id)}
        className="bg-purple-600 hover:bg-purple-700"
        data-testid={`generate-script-${idea.id}`}
      >
        <Wand2 className="w-3 h-3 mr-1" />
        Generate Script
      </Button>
    </div>
  );
}
