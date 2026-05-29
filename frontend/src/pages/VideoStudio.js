import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Film, Loader2, Download, Trash2, Play, AlertTriangle, CheckCircle2, Mic } from "lucide-react";
import { videoAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

// Faceless Video Studio — render vertical TikTok/Shorts/Reels MP4s from a script.
// Backed by: Piper TTS (free) + Pexels stock (free tier) + ffmpeg compose.
// Phase-2 modes (avatar lipsync, Sora 2 bridge) appear here once enabled on the host.

const STATUS_PILL = {
  pending: "bg-gray-500/15 text-gray-300 border-gray-500/30",
  running: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  complete: "bg-green-500/15 text-green-300 border-green-500/30",
  failed: "bg-red-500/15 text-red-300 border-red-500/30",
};

function CapabilityCard({ data }) {
  if (!data) return null;
  const facelessOk = data.modes_available?.faceless;
  return (
    <div className="metric-card mb-6" data-testid="video-capability">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Film className="w-4 h-4 text-purple-400" />
            <h3 className="text-base font-semibold text-white">Engine Capabilities</h3>
          </div>
          <p className="text-xs text-gray-500">
            Self-reported by <code>GET /api/video/config</code> — refresh after installing new deps.
          </p>
        </div>
        <div className={`text-xs px-2 py-1 rounded border ${facelessOk ? STATUS_PILL.complete : STATUS_PILL.failed}`}>
          {facelessOk ? "READY" : "DEGRADED"}
        </div>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
        <CapPill label="ffmpeg" ok={data.ffmpeg_installed} />
        <CapPill label="Piper TTS" ok={data.piper_installed} />
        <CapPill label="Voices" ok={(data.voices_installed || []).length > 0} note={`${(data.voices_installed || []).length}`} />
        <CapPill label="Pexels API" ok={data.pexels_api_key_set} note={data.pexels_api_key_set ? "live" : "fallback"} />
      </div>
      {(data.operator_actions || []).length > 0 && (
        <div className="mt-3 pt-3 border-t border-white/5">
          <p className="text-[10px] uppercase tracking-wider text-amber-300 mb-1.5">Operator actions</p>
          <ul className="text-xs text-gray-400 space-y-1 list-disc list-inside">
            {data.operator_actions.map((a) => (
              <li key={a.slice(0, 60)}>{a}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function CapPill({ label, ok, note }) {
  return (
    <div className={`px-2.5 py-1.5 rounded border ${ok ? "bg-green-500/5 border-green-500/30 text-green-300" : "bg-red-500/5 border-red-500/30 text-red-300"}`}>
      <div className="flex items-center justify-between">
        <span className="font-medium">{label}</span>
        {ok ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
      </div>
      {note && <div className="text-[10px] mt-0.5 opacity-70">{note}</div>}
    </div>
  );
}

function RenderForm({ voices, onSubmit, isSubmitting }) {
  const [hook, setHook] = useState("Stop scrolling — this changes how you think about money.");
  const [body, setBody] = useState("Most people work for money. Smart people build systems that pay them while they sleep.");
  const [cta, setCta] = useState("Follow for daily money tactics.");
  const [shots, setShots] = useState("money stack\nperson typing on laptop\ngraph going up\ncoffee morning\nphone notification");
  const [voiceId, setVoiceId] = useState("");

  const handle = () => {
    const shot_list = shots.split("\n").map((s) => s.trim()).filter(Boolean);
    if (!body.trim() && !hook.trim()) {
      toast.error("Add at least a HOOK or SCRIPT body");
      return;
    }
    if (shot_list.length < 1) {
      toast.error("Add at least 1 shot description");
      return;
    }
    onSubmit({ script: { hook, script_body: body, cta, shot_list }, voice_id: voiceId || undefined });
  };

  return (
    <div className="metric-card mb-6" data-testid="video-render-form">
      <div className="flex items-center gap-2 mb-4">
        <Film className="w-4 h-4 text-purple-400" />
        <h3 className="text-base font-semibold text-white">Render a Faceless Video</h3>
      </div>
      <div className="space-y-3">
        <div>
          <label className="text-xs text-gray-400 mb-1 block">HOOK (first 3 seconds)</label>
          <Input
            value={hook}
            onChange={(e) => setHook(e.target.value)}
            data-testid="video-hook-input"
            className="bg-black/30 border-white/10"
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">SCRIPT body</label>
          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={4}
            data-testid="video-body-input"
            className="bg-black/30 border-white/10"
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">CTA</label>
          <Input
            value={cta}
            onChange={(e) => setCta(e.target.value)}
            data-testid="video-cta-input"
            className="bg-black/30 border-white/10"
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">
            SHOT LIST (one per line — each becomes a 5-second clip)
          </label>
          <Textarea
            value={shots}
            onChange={(e) => setShots(e.target.value)}
            rows={5}
            data-testid="video-shots-input"
            className="bg-black/30 border-white/10 font-mono text-xs"
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block flex items-center gap-1.5">
            <Mic className="w-3 h-3" /> Voice
          </label>
          <select
            value={voiceId}
            onChange={(e) => setVoiceId(e.target.value)}
            className="w-full bg-black/30 border border-white/10 rounded px-3 py-2 text-sm text-white"
            data-testid="video-voice-select"
          >
            <option value="">— default —</option>
            {(voices || []).map((v) => (
              <option key={v.id} value={v.id}>{v.id}</option>
            ))}
          </select>
        </div>
        <Button
          onClick={handle}
          disabled={isSubmitting}
          className="w-full bg-purple-600 hover:bg-purple-700"
          data-testid="video-render-btn"
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
          Render Video
        </Button>
      </div>
    </div>
  );
}

function JobCard({ job, onDelete }) {
  const downloadHref = videoAPI.downloadUrl(job.id);
  return (
    <div className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-xl p-4" data-testid={`video-job-${job.id}`}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <code className="text-xs text-purple-300">{job.id}</code>
            <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase tracking-wider ${STATUS_PILL[job.status] || STATUS_PILL.pending}`}>
              {job.status}
            </span>
            <span className="text-[10px] text-gray-500">{new Date(job.created_at).toLocaleString()}</span>
          </div>
          <p className="text-xs text-gray-300 line-clamp-2 leading-snug">
            <span className="text-amber-300">{job.script?.hook?.slice(0, 80) || "—"}</span>
          </p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {job.status === "complete" && (
            <a
              href={downloadHref}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs px-2 py-1 rounded border border-green-500/30 bg-green-500/10 text-green-300 hover:bg-green-500/20 flex items-center gap-1"
              data-testid={`video-download-${job.id}`}
            >
              <Download className="w-3 h-3" /> MP4
            </a>
          )}
          <button
            onClick={() => onDelete(job.id)}
            className="text-xs px-2 py-1 rounded border border-red-500/30 bg-red-500/10 text-red-300 hover:bg-red-500/20"
            data-testid={`video-delete-${job.id}`}
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>
      {(job.status === "running" || job.status === "pending") && (
        <div className="mt-2">
          <div className="h-1.5 bg-black/40 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 transition-all"
              style={{ width: `${job.progress_pct || 0}%` }}
              data-testid={`video-progress-${job.id}`}
            />
          </div>
          <p className="text-[10px] text-gray-400 mt-1">{job.message}</p>
        </div>
      )}
      {job.status === "complete" && (
        <video
          src={downloadHref}
          controls
          preload="metadata"
          className="w-full max-h-80 mt-2 rounded bg-black"
          data-testid={`video-player-${job.id}`}
        />
      )}
      {job.status === "failed" && (
        <p className="text-xs text-red-400 mt-2 font-mono break-all" data-testid={`video-error-${job.id}`}>
          {job.error}
        </p>
      )}
    </div>
  );
}

export default function VideoStudio() {
  const queryClient = useQueryClient();

  const { data: config } = useQuery({
    queryKey: ["video-config"],
    queryFn: () => videoAPI.config().then((r) => r.data),
    refetchInterval: 30000,
  });

  const { data: voices } = useQuery({
    queryKey: ["video-voices"],
    queryFn: () => videoAPI.voices().then((r) => r.data.installed),
  });

  const { data: jobs = [] } = useQuery({
    queryKey: ["video-jobs"],
    queryFn: () => videoAPI.jobs(20).then((r) => r.data),
    refetchInterval: (q) => {
      const rows = q.state.data || [];
      return rows.some((j) => j.status === "running" || j.status === "pending") ? 3000 : 15000;
    },
  });

  const render = useMutation({
    mutationFn: (payload) => videoAPI.render(payload).then((r) => r.data),
    onSuccess: (data) => {
      toast.success(`Render queued: ${data.job_id}`);
      queryClient.invalidateQueries({ queryKey: ["video-jobs"] });
    },
    onError: (e) => {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Render failed — check engine status");
    },
  });

  const del = useMutation({
    mutationFn: (id) => videoAPI.deleteJob(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["video-jobs"] }),
  });

  return (
    <div className="space-y-6" data-testid="video-studio-page">
      <div>
        <h1 className="text-3xl font-bold text-white">Video Engine</h1>
        <p className="text-sm text-gray-400 mt-1">
          $0/mo faceless-video pipeline. Piper TTS + Pexels stock + ffmpeg.
          Renders vertical 1080×1920 MP4s ready for TikTok / Shorts / Reels.
        </p>
      </div>
      <CapabilityCard data={config} />
      <RenderForm
        voices={voices}
        onSubmit={(payload) => render.mutate(payload)}
        isSubmitting={render.isPending}
      />
      <div>
        <h3 className="text-base font-semibold text-white mb-3">Recent Renders</h3>
        {jobs.length === 0 ? (
          <div className="text-center py-12 text-sm text-gray-500" data-testid="video-jobs-empty">
            No renders yet. Submit the form above.
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} onDelete={(id) => del.mutate(id)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
