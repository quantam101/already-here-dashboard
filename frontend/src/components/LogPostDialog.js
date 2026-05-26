import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { publishingAPI, revenueAPI } from "../lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const PLATFORMS = [
  "blog", "medium", "youtube", "tiktok", "instagram",
  "linkedin", "etsy", "redbubble", "reddit", "newsletter", "twitter",
];

const INITIAL = {
  stream_id: "",
  platform: "blog",
  title: "",
  status: "posted",
  post_url: "",
  notes: "",
};

export default function LogPostDialog() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(INITIAL);

  const { data: streams = [] } = useQuery({
    queryKey: ["revenueStreams"],
    queryFn: () => revenueAPI.getAll().then((r) => r.data),
    enabled: open,
  });

  const create = useMutation({
    mutationFn: (payload) => publishingAPI.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publishing"] });
      queryClient.invalidateQueries({ queryKey: ["publishingStats"] });
      toast.success("Post logged to publishing record");
      setOpen(false);
      setForm(INITIAL);
    },
    onError: (err) => {
      const detail = err?.response?.data?.detail || err.message;
      toast.error(`Failed: ${detail}`);
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.stream_id) return toast.error("Pick a stream");
    if (!form.title.trim()) return toast.error("Title required");
    create.mutate({
      stream_id: form.stream_id,
      platform: form.platform,
      title: form.title.trim(),
      status: form.status,
      post_url: form.post_url || null,
      notes: form.notes || null,
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="border-blue-500/30 text-blue-300 hover:bg-blue-500/10"
          data-testid="log-post-trigger"
        >
          <Send className="w-4 h-4 mr-1.5" />
          Log Post
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#0f1419] border-white/10 text-white max-w-md">
        <DialogHeader>
          <DialogTitle>Log a Published Post</DialogTitle>
          <DialogDescription className="text-gray-400 text-sm">
            Record a content distribution event. Use status &quot;posted&quot; with a URL to mark it live, &quot;verified&quot; once metrics are confirmed.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4" data-testid="log-post-form">
          <div>
            <Label htmlFor="stream_id_post">Revenue Stream</Label>
            <select
              id="stream_id_post"
              value={form.stream_id}
              onChange={(e) => setForm({ ...form, stream_id: e.target.value })}
              className="mt-1 w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
              data-testid="log-post-stream"
              required
            >
              <option value="">Select a stream...</option>
              {streams.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="platform">Platform</Label>
              <select
                id="platform"
                value={form.platform}
                onChange={(e) => setForm({ ...form, platform: e.target.value })}
                className="mt-1 w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
                data-testid="log-post-platform"
              >
                {PLATFORMS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="status">Status</Label>
              <select
                id="status"
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className="mt-1 w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
                data-testid="log-post-status"
              >
                <option value="drafted">drafted</option>
                <option value="exported">exported</option>
                <option value="posted">posted</option>
                <option value="verified">verified</option>
              </select>
            </div>
          </div>
          <div>
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white"
              placeholder="What did you publish?"
              data-testid="log-post-title"
              required
            />
          </div>
          <div>
            <Label htmlFor="post_url">Post URL</Label>
            <Input
              id="post_url"
              type="url"
              placeholder="https://..."
              value={form.post_url}
              onChange={(e) => setForm({ ...form, post_url: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white"
              data-testid="log-post-url"
            />
          </div>
          <div>
            <Label htmlFor="notes_post">Notes</Label>
            <Input
              id="notes_post"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white"
              data-testid="log-post-notes"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={create.isPending}
              className="bg-blue-600 hover:bg-blue-700 text-white"
              data-testid="log-post-submit"
            >
              {create.isPending ? "Logging..." : "Log Post"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
