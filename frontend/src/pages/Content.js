import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { FileText } from "lucide-react";
import { contentAPI } from "../lib/api";
import { toast } from "sonner";
import ContentLibraryCard from "../components/ContentLibraryCard";
import ContentGenerateDialog from "../components/ContentGenerateDialog";

const INITIAL_FORM = {
  content_type: "blog",
  topic: "",
  platform: "",
  tone: "professional",
  length: "medium",
  keywords: "",
};

function ContentStats({ content }) {
  const stats = [
    { label: "Total", value: content.length, accent: "text-blue-400" },
    { label: "Published", value: content.filter((c) => c.status === "published").length, accent: "text-green-400" },
    { label: "Draft", value: content.filter((c) => c.status === "draft").length, accent: "text-yellow-400" },
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
      accent: "text-purple-400",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      {stats.map((stat) => (
        <div key={stat.label} className="stat-card">
          <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">{stat.label}</p>
          <p className={`text-3xl font-bold ${stat.accent}`}>{stat.value}</p>
        </div>
      ))}
    </div>
  );
}

function ContentEmptyState() {
  return (
    <div className="text-center py-12" data-testid="no-content-message">
      <FileText className="w-12 h-12 text-gray-500 mx-auto mb-4" />
      <p className="text-gray-300 mb-2">No content yet</p>
      <p className="text-sm text-gray-500">Generate your first AI-powered content piece</p>
    </div>
  );
}

export default function Content() {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [formData, setFormData] = useState(INITIAL_FORM);

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
      setFormData(INITIAL_FORM);
    },
    onError: (error) => {
      toast.error(`Failed to generate content: ${error.message}`);
      setIsGenerating(false);
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsGenerating(true);
    const keywords = formData.keywords.split(",").map((k) => k.trim()).filter(Boolean);
    generateMutation.mutate({ ...formData, keywords });
  };

  return (
    <div data-testid="content-page" className="p-6 dark-themed-page">
      <div className="page-header flex items-center justify-between gap-4">
        <div>
          <h1>Content Library</h1>
          <p>AI-powered content generation for blogs, social media, and proposals</p>
        </div>
        <ContentGenerateDialog
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
          formData={formData}
          setFormData={setFormData}
          onSubmit={handleSubmit}
          isGenerating={isGenerating}
        />
      </div>

      <ContentStats content={content} />

      <div className="metric-card">
        <h3 className="text-lg font-semibold text-white mb-6">Content Library</h3>
        {content.length === 0 ? (
          <ContentEmptyState />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="content-list">
            {content.map((item) => (
              <ContentLibraryCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
