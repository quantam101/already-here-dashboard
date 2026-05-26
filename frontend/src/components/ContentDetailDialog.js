import { useState } from "react";
import { Copy, ExternalLink } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

function copy(text, label = "Content") {
  if (!text) return;
  navigator.clipboard.writeText(text);
  toast.success(`${label} copied to clipboard`);
}

export default function ContentDetailDialog({ item, open, onOpenChange }) {
  const [copied, setCopied] = useState(false);
  if (!item) return null;

  const url = item.url || item.proof_url || item.metadata?.url || null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="bg-[#0f1419] border-white/10 text-white max-w-2xl max-h-[85vh] overflow-y-auto"
        data-testid="content-detail-dialog"
      >
        <DialogHeader>
          <DialogTitle className="text-white pr-8 break-words">{item.title}</DialogTitle>
          <DialogDescription className="text-gray-400 text-xs flex flex-wrap items-center gap-2">
            <span className="content-badge bg-blue-500/15 text-blue-300 border border-blue-500/20">
              {item.content_type}
            </span>
            {item.platform && (
              <span className="content-badge bg-purple-500/15 text-purple-300 border border-purple-500/20">
                {item.platform}
              </span>
            )}
            <span className="content-badge status-badge-active">{item.status}</span>
            <span>· {new Date(item.created_at).toLocaleString()}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-500 uppercase tracking-wider">Body</p>
              <Button
                size="sm"
                variant="outline"
                className="border-green-500/30 text-green-300 hover:bg-green-500/10 h-7"
                onClick={() => { copy(item.body, "Content body"); setCopied(true); }}
                data-testid="copy-body"
              >
                <Copy className="w-3.5 h-3.5 mr-1.5" /> {copied ? "Copied" : "Copy"}
              </Button>
            </div>
            <pre className="whitespace-pre-wrap break-words text-sm text-gray-200 bg-black/40 border border-white/5 rounded-lg p-4 font-mono">
              {item.body || "(empty body)"}
            </pre>
          </div>

          {item.metadata?.keywords?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Keywords</p>
              <div className="flex flex-wrap gap-1.5">
                {item.metadata.keywords.map((k) => (
                  <span key={k} className="content-badge bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          )}

          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-blue-400 hover:underline"
              data-testid="open-url"
            >
              <ExternalLink className="w-4 h-4" /> Open published URL
            </a>
          )}

          <div className="border-t border-white/10 pt-3 text-xs text-gray-500">
            <p>To post this: click <span className="text-green-400">Copy</span> above, paste into your platform, then click <span className="text-yellow-400">Log Post</span> on the Command Center to record where it went.</p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
