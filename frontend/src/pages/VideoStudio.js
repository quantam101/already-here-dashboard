import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Film, Loader2, Download, Trash2, Play, AlertTriangle, CheckCircle2, Mic, Sparkles, Wand2, Music2, Image as ImageIcon, UploadCloud } from "lucide-react";
import { videoAPI, hooksAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { GenerativeSuite } from "../components/GenerativeSuite";

// Faceless Video Studio — render vertical TikTok/Shorts/Reels MP4s from a script.
// Backed by: Piper TTS (free) + Pexels stock (free tier) + ffmpeg compose.
// Phase-2 modes (avatar lipsync, Sora 2 bridge) appear here once enabled on the host.

const STATUS_PILL = {
  pending: "bg-gray-500/15 text-gray-300 border-gray-500/30",
  running: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  complete: "bg-green-500/15 text-green-300 border-green-500/30",
  failed: "bg-red-500/15 text-red-300 border-red-500/30",
};

function HookGeneratorButton({ currentHook, onPicked }) {
  const [open, setOpen] = useState(false);
  const [topic, setTopic] = useState(currentHook || "");
  const [niche, setNiche] = useState("personal finance");
  const [loading, setLoading] = useState(false);
  const [variants, setVariants] = useState([]);

  const generate = async () => {
    if (!topic.trim()) {
      toast.error("Enter a topic first");
      return;
    }
    setLoading(true);
    try {
      const r = await hooksAPI.generate({ topic, niche, count: 5 });
      setVariants(r.data.variants || []);
    } catch (e) {
      toast.error(`Hook generator failed: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-[11px] text-purple-300 hover:text-purple-100 flex items-center gap-1"
        data-testid="hook-generator-toggle"
      >
        <Sparkles className="w-3 h-3" /> AI hook generator
      </button>
    );
  }
  return (
    <div className="absolute right-4 top-auto mt-1 z-10 bg-[rgba(15,20,35,0.97)] backdrop-blur border border-purple-500/40 rounded-lg p-3 w-[min(420px,90vw)] shadow-2xl"
         data-testid="hook-generator-panel">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-purple-200 flex items-center gap-1.5">
          <Sparkles className="w-3 h-3" /> Viral Hook Generator
        </span>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-white text-xs">×</button>
      </div>
      <div className="space-y-2 mb-2">
        <Input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Topic / proof point"
          className="bg-black/40 border-white/10 text-xs h-8"
          data-testid="hook-gen-topic"
        />
        <Input
          value={niche}
          onChange={(e) => setNiche(e.target.value)}
          placeholder="Niche (e.g. personal finance, weird local history)"
          className="bg-black/40 border-white/10 text-xs h-8"
          data-testid="hook-gen-niche"
        />
        <Button
          onClick={generate}
          disabled={loading}
          size="sm"
          className="w-full bg-purple-600 hover:bg-purple-700 h-7 text-xs"
          data-testid="hook-gen-run"
        >
          {loading ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Sparkles className="w-3 h-3 mr-1" />}
          Generate 5 hook variants
        </Button>
      </div>
      {variants.length > 0 && (
        <div className="space-y-1.5 mt-2 pt-2 border-t border-white/10 max-h-72 overflow-y-auto">
          {variants.map((v) => (
            <button
              key={v.pattern + v.hook}
              type="button"
              onClick={() => { onPicked(v.hook); setOpen(false); }}
              className="w-full text-left p-2 rounded hover:bg-purple-500/15 border border-transparent hover:border-purple-500/30 transition-all"
              data-testid={`hook-pick-${v.pattern}`}
            >
              <div className="text-[10px] uppercase tracking-wider text-purple-300/70 mb-0.5">{v.pattern.replace(/_/g, " ")}</div>
              <div className="text-xs text-white leading-snug">{v.hook}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

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
        <CapPill label="BG Music" ok={(data.music_tracks_available || []).length > 0} note={`${(data.music_tracks_available || []).length} tracks`} />
        <CapPill label="Adaptive captions" ok={!!data.adaptive_captions_available} note={data.adaptive_captions_available ? "whisper local" : "uniform only"} />
        <CapPill label="MediaPipe" ok={data.mediapipe_installed} note={data.mediapipe_installed ? "face-aware" : "ken-burns"} />
        <CapPill label="Sora bridge" ok={data.external_provider_configured} note={data.external_provider_configured ? "wired" : "off"} />
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

function RenderForm({ voices, capability, music, voiceRefId, aiMusicPrompt, pollinationsVoice, onSubmit, isSubmitting }) {
  const [hook, setHook] = useState("Stop scrolling — this changes how you think about money.");
  const [body, setBody] = useState("Most people work for money. Smart people build systems that pay them while they sleep.");
  const [cta, setCta] = useState("Follow for daily money tactics.");
  const [shots, setShots] = useState("money stack\nperson typing on laptop\ngraph going up\ncoffee morning\nphone notification");
  const [voiceId, setVoiceId] = useState("");
  const [mode, setMode] = useState("faceless");
  const [portraitId, setPortraitId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [musicId, setMusicId] = useState("");
  const [adaptiveCaptions, setAdaptiveCaptions] = useState(false);

  const queryClient = useQueryClient();
  const { data: portraits = [] } = useQuery({
    queryKey: ["video-portraits"],
    queryFn: () => videoAPI.listPortraits().then((r) => r.data),
  });

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const r = await videoAPI.uploadPortrait(file);
      setPortraitId(r.data.portrait_id);
      toast.success(`Portrait uploaded: ${r.data.portrait_id}`);
      queryClient.invalidateQueries({ queryKey: ["video-portraits"] });
    } catch (err) {
      toast.error(`Upload failed: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handle = () => {
    const shot_list = shots.split("\n").map((s) => s.trim()).filter(Boolean);
    if (!body.trim() && !hook.trim()) {
      toast.error("Add at least a HOOK or SCRIPT body");
      return;
    }
    if (mode === "faceless" && shot_list.length < 1) {
      toast.error("Faceless mode needs at least 1 shot description");
      return;
    }
    if (mode === "avatar_lipsync" && !portraitId) {
      toast.error("Avatar mode requires uploading a portrait first");
      return;
    }
    onSubmit({
      script: { hook, script_body: body, cta, shot_list },
      voice_id: voiceId || undefined,
      mode,
      portrait_id: mode === "avatar_lipsync" ? portraitId : undefined,
      music_id: musicId || undefined,
      adaptive_captions: adaptiveCaptions,
      voice_ref_id: voiceRefId || undefined,
      ai_music_prompt: aiMusicPrompt || undefined,
      pollinations_voice: pollinationsVoice || undefined,
    });
  };

  const modeAvailable = (m) => capability?.modes_available?.[m];

  return (
    <div className="metric-card mb-6" data-testid="video-render-form">
      <div className="flex items-center gap-2 mb-4">
        <Film className="w-4 h-4 text-purple-400" />
        <h3 className="text-base font-semibold text-white">Render a Video</h3>
      </div>
      <div className="space-y-3">
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Render Mode</label>
          <div className="grid grid-cols-3 gap-2">
            <ModePill id="faceless" current={mode} setCurrent={setMode}
              ok={modeAvailable("faceless")} label="Faceless" subtitle="Stock + TTS — $0" />
            <ModePill id="avatar_lipsync" current={mode} setCurrent={setMode}
              ok={modeAvailable("avatar_lipsync")} label="AI Avatar" subtitle="Portrait + TTS — $0" />
            <ModePill id="external_provider" current={mode} setCurrent={setMode}
              ok={modeAvailable("external_provider")} label="Generative AI" subtitle="Sora 2 — paid" />
          </div>
        </div>

        {mode === "avatar_lipsync" && (
          <div className="bg-purple-500/5 border border-purple-500/20 rounded p-3 space-y-2">
            <label className="text-xs text-purple-300 block">Portrait image (face photo, jpg/png/webp, &lt;10MB)</label>
            <div className="flex gap-2">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleUpload}
                disabled={uploading}
                className="text-xs text-gray-300 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:bg-purple-600 file:text-white"
                data-testid="video-portrait-upload"
              />
              {portraits.length > 0 && (
                <select
                  value={portraitId}
                  onChange={(e) => setPortraitId(e.target.value)}
                  className="text-xs bg-black/30 border border-white/10 rounded px-2 py-1 text-white"
                  data-testid="video-portrait-select"
                >
                  <option value="">— pick existing —</option>
                  {portraits.map((p) => (
                    <option key={p.portrait_id} value={p.portrait_id}>{p.portrait_id}</option>
                  ))}
                </select>
              )}
            </div>
            {portraitId && (
              <p className="text-[10px] text-purple-200 font-mono">selected: {portraitId}</p>
            )}
            <p className="text-[10px] text-gray-500 leading-relaxed">
              Output watermarked "AI-generated" by default. Animated-portrait pipeline (free, no GPU) — for true Wav2Lip lipsync, drop a model at <code>/app/data/lipsync_models/wav2lip.onnx</code>.
            </p>
          </div>
        )}

        {mode === "external_provider" && (
          <div className="bg-amber-500/5 border border-amber-500/20 rounded p-3">
            <p className="text-xs text-amber-200 leading-relaxed">
              Generative AI mode uses an external provider (Sora 2 / Veo). Each render costs $0.50–$2 against your{" "}
              <code>OPENAI_VIDEO_KEY</code> / <code>LLM_API_KEY</code>. Renders above{" "}
              <code>EXTERNAL_VIDEO_GATE_USD</code> route through HITL <code>capital_allocation</code> gate.
            </p>
          </div>
        )}

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-gray-400">HOOK (first 3 seconds — the differentiator)</label>
            <HookGeneratorButton
              currentHook={hook}
              onPicked={(h) => setHook(h)}
            />
          </div>
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
        {mode === "faceless" && (
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
        )}
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

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Background music ($0/mo, CC0)</label>
            <select
              value={musicId}
              onChange={(e) => setMusicId(e.target.value)}
              className="w-full bg-black/30 border border-white/10 rounded px-3 py-2 text-sm text-white"
              data-testid="video-music-select"
            >
              <option value="">— none —</option>
              {(music || []).map((m) => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Captions</label>
            <button
              type="button"
              onClick={() => setAdaptiveCaptions((v) => !v)}
              disabled={!capability?.adaptive_captions_available}
              data-testid="video-adaptive-captions-toggle"
              className={`w-full text-left text-xs px-3 py-2 rounded border transition-colors ${
                adaptiveCaptions
                  ? "border-emerald-400 bg-emerald-500/15 text-emerald-100"
                  : "border-white/10 bg-black/20 text-gray-300 hover:border-white/30"
              } ${!capability?.adaptive_captions_available ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
            >
              <div className="font-semibold flex items-center justify-between">
                <span>{adaptiveCaptions ? "Adaptive (whisper)" : "Uniform timing"}</span>
                <span className="text-[10px] opacity-70">{adaptiveCaptions ? "ON" : "OFF"}</span>
              </div>
              <div className="text-[10px] opacity-70 mt-0.5">
                {adaptiveCaptions
                  ? "Word-level timing transcribed from TTS"
                  : "Equal duration per caption line"}
              </div>
            </button>
          </div>
        </div>
        <Button
          onClick={handle}
          disabled={isSubmitting || !modeAvailable(mode)}
          className="w-full bg-purple-600 hover:bg-purple-700"
          data-testid="video-render-btn"
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
          Render {mode === "avatar_lipsync" ? "Avatar" : mode === "external_provider" ? "Generative" : "Faceless"} Video
        </Button>

        {mode === "faceless" && (
          <ABTestButton
            topic={hook || body.slice(0, 80)}
            scriptBody={body}
            cta={cta}
            shotList={shots.split("\n").map((s) => s.trim()).filter(Boolean)}
            voiceId={voiceId}
          />
        )}
      </div>
    </div>
  );
}

function ModePill({ id, current, setCurrent, ok, label, subtitle }) {
  const active = current === id;
  return (
    <button
      onClick={() => ok && setCurrent(id)}
      disabled={!ok}
      data-testid={`video-mode-${id}`}
      className={`text-left px-3 py-2 rounded border text-xs transition-all
        ${active ? "border-purple-400 bg-purple-500/15 text-white" : "border-white/10 bg-black/20 text-gray-300 hover:border-white/30"}
        ${!ok ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
    >
      <div className="font-semibold">{label}</div>
      <div className="text-[10px] text-gray-400 mt-0.5">{subtitle}</div>
      {!ok && <div className="text-[9px] text-red-400 mt-0.5">unavailable</div>}
    </button>
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

function ABTestButton({ topic, scriptBody, cta, shotList, voiceId }) {
  const [loading, setLoading] = useState(false);
  const [batch, setBatch] = useState(null);
  const queryClient = useQueryClient();

  const fire = async () => {
    if (!topic.trim()) {
      toast.error("Add a HOOK or SCRIPT body so the topic isn't empty");
      return;
    }
    setLoading(true);
    try {
      const r = await hooksAPI.abTest({
        topic, niche: "general", script_body: scriptBody, cta,
        shot_list: shotList && shotList.length ? shotList : ["scene a", "scene b"],
        voice_id: voiceId || undefined, count: 5,
      });
      setBatch(r.data);
      toast.success(`A/B batch fired: ${r.data.job_ids.length} videos rendering in parallel`);
      queryClient.invalidateQueries({ queryKey: ["video-jobs"] });
    } catch (e) {
      toast.error(`A/B test failed: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-2" data-testid="ab-test-block">
      <button
        type="button"
        onClick={fire}
        disabled={loading}
        className="w-full text-sm py-2 px-3 rounded border border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/15 text-amber-200 flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
        data-testid="ab-test-btn"
      >
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
        Hook A/B Tester — render 5 variants in parallel
      </button>
      {batch && (
        <div className="mt-2 bg-amber-500/5 border border-amber-500/20 rounded p-2 text-xs space-y-1.5" data-testid="ab-test-result">
          <p className="text-amber-200 font-semibold">{batch.variants.length} variants rendering — scroll down to "Recent Renders":</p>
          {batch.variants.map((v, i) => (
            <div key={v.pattern + v.hook} className="flex items-start gap-2">
              <code className="text-amber-300 text-[10px] shrink-0 mt-0.5">{batch.job_ids[i]?.slice(0, 12) || ""}</code>
              <span className="text-gray-300 leading-snug">
                <span className="text-amber-300/80 uppercase text-[9px] mr-1">{v.pattern.replace(/_/g, " ")}</span>
                {v.hook}
              </span>
            </div>
          ))}
          <p className="text-gray-500 text-[10px] mt-2 pt-2 border-t border-white/5">
            Post each to a separate burner account, wait 4 hours, then re-render the full-length video with the winning hook.
          </p>
        </div>
      )}
    </div>
  );
}

export default function VideoStudio() {
  const queryClient = useQueryClient();
  const [voiceRefId, setVoiceRefId] = useState("");
  const [aiMusicPrompt, setAiMusicPrompt] = useState("");
  const [pollinationsVoice, setPollinationsVoice] = useState("");

  const { data: config } = useQuery({
    queryKey: ["video-config"],
    queryFn: () => videoAPI.config().then((r) => r.data),
    refetchInterval: 30000,
  });

  const { data: voices } = useQuery({
    queryKey: ["video-voices"],
    queryFn: () => videoAPI.voices().then((r) => r.data.installed),
  });

  const { data: music } = useQuery({
    queryKey: ["video-music"],
    queryFn: () => videoAPI.music().then((r) => r.data.available),
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
      <GenerativeSuite
        capability={config}
        voiceRefId={voiceRefId}
        setVoiceRefId={setVoiceRefId}
        aiMusicPrompt={aiMusicPrompt}
        setAiMusicPrompt={setAiMusicPrompt}
        pollinationsVoice={pollinationsVoice}
        setPollinationsVoice={setPollinationsVoice}
      />
      <RenderForm
        voices={voices}
        capability={config}
        music={music}
        voiceRefId={voiceRefId}
        aiMusicPrompt={aiMusicPrompt}
        pollinationsVoice={pollinationsVoice}
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
