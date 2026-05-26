import { useQuery } from "@tanstack/react-query";
import { Copy, ExternalLink, Wand2, Loader2 } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { studioAPI } from "../lib/api";
import { toast } from "sonner";

function copyText(text, label = "Script") {
  if (!text) return;
  navigator.clipboard.writeText(text);
  toast.success(`${label} copied to clipboard`);
}

function fullScript(s) {
  const parts = [];
  if (s.hook) parts.push(`HOOK:\n${s.hook}`);
  if (s.script_body) parts.push(`\nSCRIPT:\n${s.script_body}`);
  if (s.cta) parts.push(`\nCTA:\n${s.cta}`);
  if (s.shot_list?.length) parts.push(`\nSHOTS:\n${s.shot_list.map((x, i) => `${i + 1}. ${x}`).join("\n")}`);
  return parts.join("\n");
}

function ScriptCard({ script }) {
  return (
    <div className="bg-black/40 border border-white/10 rounded-lg p-4 space-y-3" data-testid={`script-${script.id}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">
          {new Date(script.created_at).toLocaleString()} · {script.metadata?.model || "ai"}
        </p>
        <Button
          size="sm"
          variant="outline"
          className="border-green-500/30 text-green-300 hover:bg-green-500/10 h-7"
          onClick={() => copyText(fullScript(script), "Full script")}
          data-testid={`copy-script-${script.id}`}
        >
          <Copy className="w-3.5 h-3.5 mr-1.5" /> Copy Full Script
        </Button>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Hook</p>
          <button onClick={() => copyText(script.hook, "Hook")} className="text-xs text-gray-500 hover:text-green-400">copy</button>
        </div>
        <p className="text-sm text-yellow-300 italic">{script.hook}</p>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Script Body</p>
          <button onClick={() => copyText(script.script_body, "Script body")} className="text-xs text-gray-500 hover:text-green-400">copy</button>
        </div>
        <pre className="whitespace-pre-wrap break-words text-sm text-gray-200 font-sans">{script.script_body}</pre>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Call to Action</p>
          <button onClick={() => copyText(script.cta, "CTA")} className="text-xs text-gray-500 hover:text-green-400">copy</button>
        </div>
        <p className="text-sm text-green-300">{script.cta}</p>
      </div>

      {script.shot_list?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Shot List ({script.shot_list.length})</p>
          <ol className="text-sm text-gray-300 space-y-0.5 list-decimal list-inside">
            {script.shot_list.map((s, i) => (
              <li key={`${i}-${s.slice(0, 20)}`}>{s}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

export default function IdeaDetailDialog({ idea, open, onOpenChange, onGenerateScript, isGenerating }) {
  const enabled = open && !!idea?.id;
  const { data: scripts = [], isFetching } = useQuery({
    queryKey: ["scriptsForIdea", idea?.id],
    queryFn: () => studioAPI.scriptsForIdea(idea.id).then((r) => r.data),
    enabled,
    refetchOnWindowFocus: false,
  });

  if (!idea) return null;
  const sourceUrl = idea.inspiration_source;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="bg-[#0f1419] border-white/10 text-white max-w-3xl max-h-[85vh] overflow-y-auto"
        data-testid="idea-detail-dialog"
      >
        <DialogHeader>
          <DialogTitle className="text-white pr-8 break-words">{idea.title}</DialogTitle>
          <DialogDescription className="text-gray-400 text-xs flex flex-wrap items-center gap-2">
            <span className="content-badge status-badge-active">{idea.status}</span>
            <span>· topic: {idea.topic}</span>
            <span>· {new Date(idea.created_at).toLocaleString()}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {idea.description && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Description</p>
              <p className="text-sm text-gray-200">{idea.description}</p>
            </div>
          )}

          {idea.target_platforms?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Target Platforms</p>
              <div className="flex flex-wrap gap-1.5">
                {idea.target_platforms.map((p) => (
                  <span key={p} className="content-badge bg-blue-500/10 text-blue-300 border border-blue-500/20">
                    {p}
                  </span>
                ))}
              </div>
            </div>
          )}

          {sourceUrl && (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-blue-400 hover:underline break-all"
              data-testid="open-inspiration-source"
            >
              <ExternalLink className="w-4 h-4 shrink-0" /> Inspiration source
            </a>
          )}

          <div className="border-t border-white/10 pt-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-base font-semibold text-white flex items-center gap-2">
                <Wand2 className="w-4 h-4 text-purple-400" />
                Generated Scripts ({scripts.length})
              </h4>
              <Button
                size="sm"
                onClick={() => onGenerateScript(idea.id)}
                disabled={isGenerating}
                className="bg-purple-600 hover:bg-purple-700 text-white"
                data-testid="dialog-generate-script"
              >
                {isGenerating ? (
                  <><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />Generating…</>
                ) : (
                  <><Wand2 className="w-3.5 h-3.5 mr-1.5" />{scripts.length > 0 ? "Generate Another" : "Generate Script"}</>
                )}
              </Button>
            </div>

            {isFetching && scripts.length === 0 ? (
              <p className="text-sm text-gray-400">Loading scripts…</p>
            ) : scripts.length === 0 ? (
              <div className="text-sm text-gray-400 bg-black/40 border border-white/5 rounded-lg p-4 text-center">
                No scripts yet. Click <span className="text-purple-300">Generate Script</span> — Gemini-3-Flash writes hook + body + CTA + shot list in ~5 seconds.
              </div>
            ) : (
              <div className="space-y-3">
                {scripts.map((s) => <ScriptCard key={s.id} script={s} />)}
              </div>
            )}
          </div>

          <div className="border-t border-white/10 pt-3 text-xs text-gray-500">
            <p>
              <span className="text-green-400">How to post:</span> Click <span className="text-green-400">Copy Full Script</span>, paste into the platform (TikTok/Reddit/LinkedIn etc.), publish, then come to{" "}
              <a href="/proof-of-work" className="text-blue-400 hover:underline">/proof-of-work</a>{" "}and click <span className="text-yellow-400">Log Post</span> with the live URL so the funnel tracks it.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
