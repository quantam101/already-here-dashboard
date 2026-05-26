import { Button } from "@/components/ui/button";
import { Wand2, FileText } from "lucide-react";

export default function IdeaCard({ idea, onGenerateScript, onClick, scriptCount = 0 }) {
  const hasScripts = scriptCount > 0 || idea.status === "scripted";
  return (
    <button
      type="button"
      onClick={() => onClick?.(idea)}
      className="text-left w-full enterprise-card hover:border-purple-500/40 hover:bg-[rgba(23,27,40,0.7)] transition-colors cursor-pointer"
      data-testid={`idea-${idea.id}`}
    >
      <div className="flex items-start justify-between mb-3 gap-2">
        <div className="flex-1 min-w-0">
          <h4 className="text-white font-semibold mb-1 line-clamp-2">{idea.title}</h4>
          {idea.description && (
            <p className="text-gray-400 text-sm line-clamp-2">{idea.description}</p>
          )}
        </div>
        <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-xs shrink-0">
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
      <div className="flex items-center justify-between gap-2">
        <Button
          size="sm"
          onClick={(e) => { e.stopPropagation(); onGenerateScript(idea.id); }}
          className="bg-purple-600 hover:bg-purple-700"
          data-testid={`generate-script-${idea.id}`}
        >
          <Wand2 className="w-3 h-3 mr-1" />
          {hasScripts ? "Re-generate" : "Generate Script"}
        </Button>
        <span className="text-xs text-purple-300 flex items-center gap-1">
          <FileText className="w-3 h-3" />
          {hasScripts ? "View scripts →" : "Click to open"}
        </span>
      </div>
    </button>
  );
}
