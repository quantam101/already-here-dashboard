import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Sparkles, Plus, FileText, Wand2, Calendar, Send, AlertCircle, CheckCircle, Lock } from "lucide-react";
import { api } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";

const studioAPI = {
  getIdeas: () => api.get("/studio/ideas/"),
  createIdea: (data) => api.post("/studio/ideas/", data),
  generateScript: (ideaId) => api.post(`/studio/ideas/${ideaId}/script`),
  getConnectors: () => api.get("/studio/connectors/"),
  getScheduled: () => api.get("/studio/schedule/"),
  scheduleP: (data) => api.post("/studio/schedule/", data),
};

const COST_CLASS_CONFIG = {
  free_local: { color: "text-green-400", bg: "bg-green-500/20", border: "border-green-500/30", icon: CheckCircle, label: "FREE LOCAL" },
  free_external: { color: "text-blue-400", bg: "bg-blue-500/20", border: "border-blue-500/30", icon: CheckCircle, label: "FREE API" },
  free_with_limits: { color: "text-cyan-400", bg: "bg-cyan-500/20", border: "border-cyan-500/30", icon: AlertCircle, label: "FREE LIMITED" },
  manual_free: { color: "text-yellow-400", bg: "bg-yellow-500/20", border: "border-yellow-500/30", icon: AlertCircle, label: "MANUAL EXPORT" },
  unknown_cost_blocked: { color: "text-orange-400", bg: "bg-orange-500/20", border: "border-orange-500/30", icon: Lock, label: "UNKNOWN COST" },
  paid_blocked: { color: "text-red-400", bg: "bg-red-500/20", border: "border-red-500/30", icon: Lock, label: "PAID - BLOCKED" },
};

function IdeaCard({ idea, onGenerateScript }) {
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

function ConnectorCard({ connector }) {
  const config = COST_CLASS_CONFIG[connector.cost_class] || COST_CLASS_CONFIG.unknown_cost_blocked;
  const Icon = config.icon;

  return (
    <div className={`enterprise-card border ${config.border}`} data-testid={`connector-${connector.id}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="text-white font-semibold mb-1">{connector.name}</h4>
          <span className={`px-2 py-1 rounded text-xs font-bold ${config.bg} ${config.color}`}>
            <Icon className="w-3 h-3 inline mr-1" />
            {config.label}
          </span>
        </div>
      </div>
      <div className="text-xs text-gray-400 space-y-1">
        <div>API: {connector.has_api ? "Yes" : "No"}</div>
        <div>Auth: {connector.api_authenticated ? "Configured" : "Missing"}</div>
        <div>Credentials: {connector.credential_status}</div>
        {connector.blocked_reason && (
          <div className="mt-2 p-2 bg-gray-900/50 rounded text-xs text-gray-300">
            <span className="font-semibold">Blocked:</span> {connector.blocked_reason}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ContentStudio() {
  const queryClient = useQueryClient();
  const [ideaDialogOpen, setIdeaDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    topic: "",
    target_platforms: [],
  });

  const { data: ideas = [] } = useQuery({
    queryKey: ["studioIdeas"],
    queryFn: () => studioAPI.getIdeas().then((res) => res.data),
  });

  const { data: connectors = [] } = useQuery({
    queryKey: ["studioConnectors"],
    queryFn: () => studioAPI.getConnectors().then((res) => res.data),
  });

  const { data: scheduled = [] } = useQuery({
    queryKey: ["studioScheduled"],
    queryFn: () => studioAPI.getScheduled().then((res) => res.data),
  });

  const createIdeaMutation = useMutation({
    mutationFn: studioAPI.createIdea,
    onSuccess: () => {
      queryClient.invalidateQueries(["studioIdeas"]);
      toast.success("Idea created!");
      setIdeaDialogOpen(false);
      setFormData({ title: "", description: "", topic: "", target_platforms: [] });
    },
    onError: (e) => toast.error(`Failed: ${e.message}`),
  });

  const generateScriptMutation = useMutation({
    mutationFn: studioAPI.generateScript,
    onSuccess: () => {
      queryClient.invalidateQueries(["studioIdeas"]);
      toast.success("Script generated by AI!");
    },
    onError: (e) => toast.error(`Failed: ${e.message}`),
  });

  const togglePlatform = (platform) => {
    setFormData((prev) => ({
      ...prev,
      target_platforms: prev.target_platforms.includes(platform)
        ? prev.target_platforms.filter((p) => p !== platform)
        : [...prev.target_platforms, platform],
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    createIdeaMutation.mutate(formData);
  };

  // Cost compliance stats
  const freeConnectors = connectors.filter((c) => c.cost_class.startsWith("free")).length;
  const manualConnectors = connectors.filter((c) => c.cost_class === "manual_free").length;
  const blockedConnectors = connectors.filter((c) => c.cost_class === "paid_blocked").length;

  return (
    <div className="p-6 space-y-6" data-testid="content-studio-page">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1" style={{ fontFamily: 'Space Grotesk' }}>
            Content Factory
          </h1>
          <p className="text-gray-400 text-sm">
            CapCut-style production · Zero-cost · {connectors.length} platforms configured
          </p>
        </div>
        <Dialog open={ideaDialogOpen} onOpenChange={setIdeaDialogOpen}>
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
            <form onSubmit={handleSubmit} className="space-y-4">
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
                  {["tiktok", "youtube", "instagram", "linkedin", "blog", "medium"].map((p) => (
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
      </div>

      {/* Cost Compliance */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="metric-card-enterprise">
          <div className="text-gray-400 text-sm mb-2">TOTAL IDEAS</div>
          <div className="text-3xl font-bold text-white">{ideas.length}</div>
        </div>
        <div className="metric-card-enterprise">
          <div className="text-gray-400 text-sm mb-2">FREE CONNECTORS</div>
          <div className="text-3xl font-bold text-green-400">{freeConnectors}</div>
          <div className="text-xs text-gray-400 mt-1">$0/month</div>
        </div>
        <div className="metric-card-enterprise">
          <div className="text-gray-400 text-sm mb-2">MANUAL EXPORT</div>
          <div className="text-3xl font-bold text-yellow-400">{manualConnectors}</div>
          <div className="text-xs text-gray-400 mt-1">awaiting API setup</div>
        </div>
        <div className="metric-card-enterprise">
          <div className="text-gray-400 text-sm mb-2">PAID BLOCKED</div>
          <div className="text-3xl font-bold text-red-400">{blockedConnectors}</div>
          <div className="text-xs text-gray-400 mt-1">Cost Guard active</div>
        </div>
      </div>

      <Tabs defaultValue="ideas" className="w-full">
        <TabsList className="bg-gray-900 border border-gray-800">
          <TabsTrigger value="ideas" data-testid="tab-ideas">Ideas ({ideas.length})</TabsTrigger>
          <TabsTrigger value="connectors" data-testid="tab-connectors">Connectors ({connectors.length})</TabsTrigger>
          <TabsTrigger value="scheduled" data-testid="tab-scheduled">Scheduled ({scheduled.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="ideas" className="mt-6">
          {ideas.length === 0 ? (
            <div className="enterprise-card text-center py-12">
              <Sparkles className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No content ideas yet</p>
              <p className="text-gray-500 text-sm mt-1">Create your first idea to start the pipeline</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {ideas.map((idea) => (
                <IdeaCard
                  key={idea.id}
                  idea={idea}
                  onGenerateScript={(id) => generateScriptMutation.mutate(id)}
                />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="connectors" className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {connectors.map((connector) => (
              <ConnectorCard key={connector.id} connector={connector} />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="scheduled" className="mt-6">
          {scheduled.length === 0 ? (
            <div className="enterprise-card text-center py-12">
              <Calendar className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No scheduled posts</p>
            </div>
          ) : (
            <div className="space-y-3">
              {scheduled.map((post) => (
                <div key={post.id} className="enterprise-card flex items-center justify-between">
                  <div>
                    <div className="text-white font-medium">{post.title || "Untitled"}</div>
                    <div className="text-gray-400 text-sm">{post.platform} · {post.status}</div>
                  </div>
                  <div className="text-gray-400 text-xs">
                    {new Date(post.scheduled_time).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
