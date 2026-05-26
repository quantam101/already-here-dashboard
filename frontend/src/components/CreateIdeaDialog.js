import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus } from "lucide-react";

const AVAILABLE_PLATFORMS = ["tiktok", "youtube", "instagram", "linkedin", "blog", "medium"];

export default function CreateIdeaDialog({ open, onOpenChange, formData, setFormData, onSubmit }) {
  const togglePlatform = (platform) => {
    setFormData((prev) => ({
      ...prev,
      target_platforms: prev.target_platforms.includes(platform)
        ? prev.target_platforms.filter((p) => p !== platform)
        : [...prev.target_platforms, platform],
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-purple-600 hover:bg-purple-700" data-testid="new-idea-btn">
          <Plus className="w-4 h-4 mr-2" />
          New Content Idea
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-gray-900 border-gray-700 text-white">
        <DialogHeader>
          <DialogTitle>Create Content Idea</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="e.g., 10 Revenue Automation Hacks"
              required
              className="bg-gray-800 border-gray-700"
              data-testid="idea-title-input"
            />
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="What's this content about?"
              required
              className="bg-gray-800 border-gray-700"
              data-testid="idea-description-input"
            />
          </div>
          <div>
            <Label htmlFor="topic">Topic / Niche</Label>
            <Input
              id="topic"
              value={formData.topic}
              onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
              placeholder="e.g., business automation"
              required
              className="bg-gray-800 border-gray-700"
              data-testid="idea-topic-input"
            />
          </div>
          <div>
            <Label>Target Platforms</Label>
            <div className="flex flex-wrap gap-2 mt-2">
              {AVAILABLE_PLATFORMS.map((p) => (
                <button
                  type="button"
                  key={p}
                  onClick={() => togglePlatform(p)}
                  className={`px-3 py-1 rounded text-xs ${
                    formData.target_platforms.includes(p)
                      ? "bg-purple-500/30 text-purple-400 border border-purple-500/50"
                      : "bg-gray-800 text-gray-400 border border-gray-700"
                  }`}
                  data-testid={`platform-${p}`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <Button type="submit" className="w-full" data-testid="submit-idea-btn">
            Create Idea
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
