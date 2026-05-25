import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { FileText, Plus, Sparkles } from "lucide-react";
import { contentAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

export default function Content() {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [formData, setFormData] = useState({
    content_type: "blog",
    topic: "",
    platform: "",
    tone: "professional",
    length: "medium",
    keywords: "",
  });

  const { data: content = [] } = useQuery({
    queryKey: ["content"],
    queryFn: () => contentAPI.getAll().then((res) => res.data),
  });

  const generateMutation = useMutation({
    mutationFn: contentAPI.generate,
    onSuccess: () => {
      queryClient.invalidateQueries(["content"]);
      toast.success("Content generated successfully!");
      setIsDialogOpen(false);
      setIsGenerating(false);
      setFormData({
        content_type: "blog",
        topic: "",
        platform: "",
        tone: "professional",
        length: "medium",
        keywords: "",
      });
    },
    onError: (error) => {
      toast.error(`Failed to generate content: ${error.message}`);
      setIsGenerating(false);
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsGenerating(true);
    const keywords = formData.keywords
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);
    generateMutation.mutate({ ...formData, keywords });
  };

  return (
    <div data-testid="content-page">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1>Content Automation</h1>
          <p>AI-powered content generation for blogs, social media, and proposals</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="flex items-center gap-2" data-testid="generate-content-btn">
              <Sparkles className="w-4 h-4" />
              Generate Content
            </Button>
          </DialogTrigger>
          <DialogContent data-testid="generate-content-dialog">
            <DialogHeader>
              <DialogTitle>Generate AI Content</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="content_type">Content Type</Label>
                <Select
                  value={formData.content_type}
                  onValueChange={(value) =>
                    setFormData((prev) => ({ ...prev, content_type: value }))
                  }
                >
                  <SelectTrigger data-testid="content-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="blog">Blog Post</SelectItem>
                    <SelectItem value="social">Social Media</SelectItem>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="proposal">Proposal</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="topic">Topic</Label>
                <Input
                  id="topic"
                  value={formData.topic}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, topic: e.target.value }))
                  }
                  placeholder="What should this content be about?"
                  required
                  data-testid="content-topic-input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="tone">Tone</Label>
                  <Select
                    value={formData.tone}
                    onValueChange={(value) =>
                      setFormData((prev) => ({ ...prev, tone: value }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="professional">Professional</SelectItem>
                      <SelectItem value="casual">Casual</SelectItem>
                      <SelectItem value="technical">Technical</SelectItem>
                      <SelectItem value="persuasive">Persuasive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="length">Length</Label>
                  <Select
                    value={formData.length}
                    onValueChange={(value) =>
                      setFormData((prev) => ({ ...prev, length: value }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="short">Short</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="long">Long</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label htmlFor="keywords">Keywords (comma-separated)</Label>
                <Input
                  id="keywords"
                  value={formData.keywords}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, keywords: e.target.value }))
                  }
                  placeholder="keyword1, keyword2, keyword3"
                  data-testid="content-keywords-input"
                />
              </div>
              <Button
                type="submit"
                className="w-full"
                disabled={isGenerating}
                data-testid="submit-content-btn"
              >
                {isGenerating ? "Generating..." : "Generate with AI"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Content Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: "Total", value: content.length, color: "bg-blue-100 text-blue-600" },
          {
            label: "Published",
            value: content.filter((c) => c.status === "published").length,
            color: "bg-green-100 text-green-600",
          },
          {
            label: "Draft",
            value: content.filter((c) => c.status === "draft").length,
            color: "bg-gray-100 text-gray-600",
          },
          {
            label: "This Month",
            value: content.filter((c) => {
              const created = new Date(c.created_at);
              const now = new Date();
              return (
                created.getMonth() === now.getMonth() &&
                created.getFullYear() === now.getFullYear()
              );
            }).length,
            color: "bg-purple-100 text-purple-600",
          },
        ].map((stat) => (
          <div key={stat.label} className="stat-card">
            <p className="text-sm text-gray-600 mb-1">{stat.label}</p>
            <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Content List */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold mb-6">Content Library</h3>
        {content.length === 0 ? (
          <div className="text-center py-12" data-testid="no-content-message">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No content yet</p>
            <p className="text-sm text-gray-500">
              Generate your first AI-powered content piece
            </p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="content-list">
            {content.map((item) => (
              <div
                key={item.id}
                className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                data-testid={`content-${item.id}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h4 className="text-lg font-semibold text-gray-900 mb-1">
                      {item.title}
                    </h4>
                    <div className="flex items-center gap-2">
                      <span className="content-badge bg-blue-100 text-blue-700">
                        {item.content_type}
                      </span>
                      {item.platform && (
                        <span className="content-badge bg-purple-100 text-purple-700">
                          {item.platform}
                        </span>
                      )}
                      <span className={`content-badge status-badge-${item.status}`}>
                        {item.status}
                      </span>
                    </div>
                  </div>
                </div>
                <p className="text-sm text-gray-600 line-clamp-2">{item.body}</p>
                <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                  <span>Generated by {item.generated_by}</span>
                  <span>{new Date(item.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}