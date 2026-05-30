import { useState, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Server,
  ShieldCheck,
  Play,
  RefreshCw,
  Check,
  Volume2,
  AlertTriangle,
  Download,
  Trash2,
  Radio,
  Activity,
} from "lucide-react";
import { voiceLabAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

// ─── Constants ────────────────────────────────────────────────────────────────

const ALL_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"];

const MAX_CHARS = 4096;

const STATUS_META = {
  pending: {
    label: "QUEUED",
    color: "text-slate-400",
    bg: "bg-slate-500/15 border-slate-500/30",
    pulseDot: "bg-slate-400",
  },
  extracting: {
    label: "EXTRACTING",
    color: "text-sky-300",
    bg: "bg-sky-500/15 border-sky-500/30",
    pulseDot: "bg-sky-400 animate-pulse",
  },
  compiling: {
    label: "COMPILING",
    color: "text-violet-300",
    bg: "bg-violet-500/15 border-violet-500/30",
    pulseDot: "bg-violet-400 animate-pulse",
  },
  complete: {
    label: "COMPLETE",
    color: "text-emerald-300",
    bg: "bg-emerald-500/15 border-emerald-500/30",
    pulseDot: "bg-emerald-400",
  },
  failed: {
    label: "FAILED",
    color: "text-rose-300",
    bg: "bg-rose-500/15 border-rose-500/30",
    pulseDot: "bg-rose-400",
  },
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusPill({ status }) {
  const m = STATUS_META[status] || STATUS_META.pending;
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[10px] font-extrabold tracking-widest uppercase px-2.5 py-1 rounded border ${m.bg} ${m.color}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${m.pulseDot}`} />
      {m.label}
    </span>
  );
}

function ProgressBar({ pct, status }) {
  const barColor =
    status === "complete"
      ? "bg-emerald-500"
      : status === "failed"
      ? "bg-rose-500"
      : "bg-sky-500";
  return (
    <div className="w-full h-1.5 bg-[#1E293B] rounded-full overflow-hidden">
      <div
        className={`h-full transition-all duration-700 ease-out rounded-full ${barColor}`}
        style={{ width: `${Math.min(pct || 0, 100)}%` }}
      />
    </div>
  );
}

function VoiceChannelGrid({ voiceResults, voices }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
      {voices.map((voice) => {
        const r = voiceResults?.[voice];
        const ok = r?.status === "ok";
        const failed = r?.status === "failed";
        return (
          <div
            key={voice}
            className={`flex items-center justify-between p-3 rounded border font-mono text-xs uppercase tracking-widest transition-all ${
              ok
                ? "bg-emerald-900/20 border-emerald-500/40 text-emerald-300"
                : failed
                ? "bg-rose-900/20 border-rose-500/40 text-rose-300"
                : "bg-[#0F172A] border-[#1E293B] text-slate-500"
            }`}
          >
            <span className="font-bold">{voice}</span>
            {ok && (
              <span className="text-[9px] text-emerald-400/80">
                {((r.size_bytes || 0) / 1024).toFixed(0)} KB
              </span>
            )}
            {failed && (
              <AlertTriangle className="w-3 h-3 text-rose-400" />
            )}
            {!ok && !failed && (
              <span className="w-1.5 h-1.5 rounded-full bg-slate-600 animate-pulse" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function JobCard({ job, onDelete, onSelect, isSelected }) {
  const m = STATUS_META[job.status] || STATUS_META.pending;
  const downloadUrl = voiceLabAPI.downloadUrl(job.id);

  return (
    <div
      className={`p-4 rounded-lg border transition-all cursor-pointer ${
        isSelected
          ? "border-sky-500/60 bg-sky-900/10"
          : "border-[#1E293B] bg-[#0A0F1E] hover:border-[#334155]"
      }`}
      onClick={() => onSelect(job.id)}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusPill status={job.status} />
            <span className="text-[10px] text-slate-500 font-mono">{job.id}</span>
          </div>
          <p className="text-xs text-slate-400 truncate">
            {(job.script || "").slice(0, 80)}
            {(job.script || "").length > 80 ? "…" : ""}
          </p>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {job.status === "complete" && (
            <a
              href={downloadUrl}
              download
              onClick={(e) => e.stopPropagation()}
              className="p-1.5 rounded hover:bg-sky-500/20 text-sky-400 hover:text-sky-200 transition-colors"
              title="Download MP4"
            >
              <Download className="w-3.5 h-3.5" />
            </a>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(job.id);
            }}
            className="p-1.5 rounded hover:bg-rose-500/20 text-slate-500 hover:text-rose-300 transition-colors"
            title="Delete job"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      <ProgressBar pct={job.progress_pct} status={job.status} />
      <p className="text-[10px] text-slate-600 mt-1.5 font-mono">{job.message}</p>
    </div>
  );
}

// ─── Live job poller ──────────────────────────────────────────────────────────

function useJobPoller(jobId) {
  return useQuery({
    queryKey: ["voicelab-job", jobId],
    queryFn: () => voiceLabAPI.job(jobId).then((r) => r.data),
    enabled: !!jobId,
    refetchInterval: (data) => {
      const status = data?.status;
      if (!status || status === "complete" || status === "failed") return false;
      return 2000; // poll every 2s while running
    },
    staleTime: 0,
  });
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function VoiceLab() {
  const queryClient = useQueryClient();
  const videoRef = useRef(null);

  const [script, setScript] = useState("");
  const [selectedVoices, setSelectedVoices] = useState(new Set(ALL_VOICES));
  const [activeJobId, setActiveJobId] = useState(null);
  const [chosenVoice, setChosenVoice] = useState(null);

  // Capability check
  const { data: config } = useQuery({
    queryKey: ["voicelab-config"],
    queryFn: () => voiceLabAPI.config().then((r) => r.data),
    staleTime: 60_000,
  });

  // Jobs list
  const { data: jobs = [], refetch: refetchJobs } = useQuery({
    queryKey: ["voicelab-jobs"],
    queryFn: () => voiceLabAPI.jobs(20).then((r) => r.data),
    refetchInterval: 8000,
  });

  // Live poll for the active job
  const { data: liveJob } = useJobPoller(activeJobId);
  const activeJob = liveJob || jobs.find((j) => j.id === activeJobId);

  // When active job transitions to complete/failed, refresh the jobs list
  const prevStatus = useRef(null);
  if (activeJob?.status !== prevStatus.current) {
    prevStatus.current = activeJob?.status;
    if (activeJob?.status === "complete" || activeJob?.status === "failed") {
      refetchJobs();
    }
  }

  // Compile mutation
  const compile = useMutation({
    mutationFn: ({ s, v }) => voiceLabAPI.compile(s, v),
    onSuccess: (res) => {
      const job_id = res.data?.job_id;
      setActiveJobId(job_id);
      queryClient.invalidateQueries({ queryKey: ["voicelab-jobs"] });
      toast.success("Matrix compilation queued — polling for results…");
    },
    onError: (err) => {
      toast.error(
        err?.response?.data?.detail || err.message || "Compilation failed"
      );
    },
  });

  // Delete mutation
  const deleteJob = useMutation({
    mutationFn: (id) => voiceLabAPI.deleteJob(id),
    onSuccess: (_, id) => {
      if (activeJobId === id) setActiveJobId(null);
      queryClient.invalidateQueries({ queryKey: ["voicelab-jobs"] });
      toast.success("Job deleted");
    },
    onError: () => toast.error("Delete failed"),
  });

  const toggleVoice = useCallback((voice) => {
    setSelectedVoices((prev) => {
      const next = new Set(prev);
      if (next.has(voice)) {
        if (next.size > 1) next.delete(voice); // keep at least 1
      } else {
        next.add(voice);
      }
      return next;
    });
  }, []);

  const handleCompile = () => {
    if (!script.trim()) return;
    compile.mutate({ s: script.trim(), v: [...selectedVoices] });
  };

  const isRunning =
    activeJob?.status === "pending" ||
    activeJob?.status === "extracting" ||
    activeJob?.status === "compiling";

  const downloadUrl =
    activeJob?.status === "complete" && activeJob?.output_path
      ? voiceLabAPI.downloadUrl(activeJob.id)
      : null;

  return (
    <div className="min-h-screen bg-[#070C19] text-slate-200 font-mono p-6 space-y-6">
      {/* ── Header ── */}
      <div className="flex items-center justify-between border-b border-[#1E293B] pb-5">
        <div className="flex items-center gap-3">
          <Radio className="h-6 w-6 text-[#38BDF8] animate-pulse" />
          <div>
            <h1 className="text-sm font-black tracking-widest uppercase text-white">
              D-ASI VOICE LAB — 6-UP ANALYTICAL MATRIX
            </h1>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">
              Deterministic Parallel Processing · Zero-Hallucination Pipeline
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {config && (
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded border text-xs font-bold ${
                config.ready
                  ? "bg-emerald-900/20 border-emerald-500/40 text-emerald-300"
                  : "bg-rose-900/20 border-rose-500/40 text-rose-300"
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              {config.ready ? "SYSTEMS NOMINAL" : "FFMPEG MISSING"}
            </div>
          )}
          <div className="flex items-center gap-2 bg-[#0F172A] border border-[#334155] px-4 py-1.5 rounded text-xs font-bold text-slate-300">
            <ShieldCheck className="h-4 w-4 text-[#34D399]" />
            <span>MIL-SPEC COMPLIANT</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* ── Left panel: input + controls ── */}
        <div className="xl:col-span-2 space-y-5">
          {/* Script input */}
          <div className="bg-[#0A0F1E] border border-[#1E293B] rounded-xl p-5">
            <div className="flex justify-between items-center mb-3">
              <label className="text-[11px] uppercase tracking-wider text-slate-400 font-bold flex items-center gap-2">
                <Server className="w-3.5 h-3.5 text-[#38BDF8]" />
                Input Diagnostic Execution Script
              </label>
              <span
                className={`text-[10px] font-mono ${
                  script.length > MAX_CHARS * 0.9
                    ? "text-amber-400"
                    : "text-slate-500"
                }`}
              >
                {script.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} CHARS
              </span>
            </div>
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value.slice(0, MAX_CHARS))}
              placeholder="Enter the script payload to parse across the parallel voice extraction node architecture…"
              disabled={isRunning || compile.isPending}
              rows={6}
              className="w-full bg-[#0F172A] border border-[#334155] rounded p-4 text-xs font-mono text-emerald-400 focus:outline-none focus:border-[#38BDF8] focus:ring-1 focus:ring-[#38BDF8] transition-all disabled:opacity-50 placeholder:text-slate-600 leading-relaxed resize-none"
            />
          </div>

          {/* Voice channel selector */}
          <div className="bg-[#0A0F1E] border border-[#1E293B] rounded-xl p-5">
            <label className="block text-[11px] uppercase tracking-wider text-slate-400 font-bold mb-3">
              Active Voice Extraction Channels
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {ALL_VOICES.map((voice) => {
                const active = selectedVoices.has(voice);
                return (
                  <button
                    key={voice}
                    type="button"
                    onClick={() => toggleVoice(voice)}
                    disabled={isRunning || compile.isPending}
                    className={`flex items-center justify-between p-3 rounded border font-mono text-xs font-bold tracking-widest uppercase transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${
                      active
                        ? "bg-[#0369A1]/30 border-[#38BDF8] text-white shadow-[0_0_12px_rgba(56,189,248,0.12)]"
                        : "bg-[#0F172A] border-[#1E293B] text-slate-500 hover:border-[#334155] hover:text-slate-300"
                    }`}
                  >
                    <span>{voice}</span>
                    {active && (
                      <div className="bg-[#38BDF8] p-0.5 rounded-full">
                        <Check className="h-2.5 w-2.5 text-[#070C19] stroke-[3]" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
            <p className="text-[10px] text-slate-600 mt-2">
              {selectedVoices.size} / {ALL_VOICES.length} channels active — each executes as an independent async worker
            </p>
          </div>

          {/* Compile button */}
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={handleCompile}
              disabled={
                isRunning ||
                compile.isPending ||
                !script.trim() ||
                selectedVoices.size === 0 ||
                (config && !config.ready)
              }
              className="flex items-center gap-3 bg-gradient-to-r from-[#0284C7] to-[#0369A1] hover:from-[#0EA5E9] hover:to-[#0284C7] text-white font-extrabold text-xs uppercase tracking-widest px-6 py-3.5 rounded shadow-xl disabled:from-slate-800 disabled:to-slate-900 disabled:text-slate-500 disabled:cursor-not-allowed transition-all duration-300 border border-[#0EA5E9]/20"
            >
              {isRunning || compile.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin text-[#38BDF8]" />
                  <span>Draining Async Streams &amp; Building Matrix…</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current" />
                  <span>Instantiate {selectedVoices.size}-Channel Compiling Matrix</span>
                </>
              )}
            </button>
            {config && !config.ready && (
              <div className="flex items-center gap-2 text-rose-300 text-xs font-bold">
                <AlertTriangle className="w-4 h-4" />
                <span>ffmpeg unavailable — install on host</span>
              </div>
            )}
          </div>

          {/* Active job progress panel */}
          {activeJob && (
            <div className="bg-[#0A0F1E] border border-[#1E293B] rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <StatusPill status={activeJob.status} />
                  <span className="text-[10px] text-slate-500 font-mono">
                    {activeJob.id}
                  </span>
                </div>
                <span className="text-xs font-bold text-slate-300 font-mono">
                  {activeJob.progress_pct ?? 0}%
                </span>
              </div>

              <ProgressBar pct={activeJob.progress_pct} status={activeJob.status} />

              <p className="text-[11px] text-slate-400 font-mono">
                {activeJob.message}
              </p>

              {/* Per-voice extraction status */}
              {activeJob.voice_results &&
                Object.keys(activeJob.voice_results).length > 0 && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-2">
                      Voice Channel Extraction Status
                    </p>
                    <VoiceChannelGrid
                      voiceResults={activeJob.voice_results}
                      voices={activeJob.voices || ALL_VOICES}
                    />
                  </div>
                )}

              {/* Error display */}
              {activeJob.status === "failed" && activeJob.error && (
                <div className="bg-rose-950/30 border border-rose-800/40 rounded p-3">
                  <div className="flex items-center gap-2 text-rose-300 text-xs font-bold mb-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    PIPELINE EXCEPTION
                  </div>
                  <p className="text-[10px] text-rose-400/80 font-mono leading-relaxed">
                    {activeJob.error}
                  </p>
                </div>
              )}

              {/* Download + action buttons */}
              {activeJob.status === "complete" && downloadUrl && (
                <div className="flex items-center gap-3 pt-1">
                  <a
                    href={downloadUrl}
                    download
                    className="flex items-center gap-2 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 text-xs font-bold px-4 py-2.5 rounded transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    DOWNLOAD MATRIX MP4
                  </a>
                  <button
                    onClick={() => deleteJob.mutate(activeJob.id)}
                    className="flex items-center gap-2 text-slate-500 hover:text-rose-300 text-xs font-bold px-3 py-2.5 rounded hover:bg-rose-500/10 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    DELETE JOB
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Matrix video player */}
          {activeJob?.status === "complete" && downloadUrl && (
            <div className="bg-[#0A0F1E] border border-[#1E293B] rounded-xl p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-[#38BDF8]" />
                <span className="text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                  6-Up Synchronous Visual / Audio Comparison Field
                </span>
              </div>
              <div className="relative border border-[#334155] bg-black rounded-lg overflow-hidden aspect-video">
                <video
                  ref={videoRef}
                  src={downloadUrl}
                  controls
                  className="w-full h-full"
                  key={downloadUrl}
                />
              </div>

              {/* Signature voice selector */}
              <div>
                <p className="text-[11px] uppercase tracking-wider text-slate-400 font-bold mb-2.5">
                  Lock Chosen Signature Voice Target System
                </p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {(activeJob.voices || ALL_VOICES).map((voice) => (
                    <button
                      key={voice}
                      type="button"
                      onClick={() =>
                        setChosenVoice((prev) => (prev === voice ? null : voice))
                      }
                      className={`flex items-center justify-between p-3.5 rounded border font-mono text-xs font-bold tracking-widest uppercase transition-all duration-200 ${
                        chosenVoice === voice
                          ? "bg-[#0369A1]/30 border-[#38BDF8] text-white shadow-[0_0_15px_rgba(56,189,248,0.15)]"
                          : "bg-[#0F172A] border-[#1E293B] text-slate-400 hover:border-[#334155] hover:text-slate-200"
                      }`}
                    >
                      <span>{voice}</span>
                      {chosenVoice === voice && (
                        <div className="bg-[#38BDF8] p-1 rounded-full">
                          <Check className="h-3 w-3 text-[#070C19] stroke-[3]" />
                        </div>
                      )}
                    </button>
                  ))}
                </div>
                {chosenVoice && (
                  <p className="text-[10px] text-[#38BDF8] mt-2 font-mono">
                    ✓ Signature voice locked:{" "}
                    <span className="font-bold uppercase">{chosenVoice}</span>
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Right panel: jobs history ── */}
        <div className="xl:col-span-1 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-[11px] uppercase tracking-wider text-slate-400 font-bold">
              Compilation Job Registry
            </h2>
            <button
              onClick={() =>
                queryClient.invalidateQueries({ queryKey: ["voicelab-jobs"] })
              }
              className="text-slate-500 hover:text-slate-300 transition-colors"
              title="Refresh jobs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          {jobs.length === 0 ? (
            <div className="bg-[#0A0F1E] border border-[#1E293B] rounded-xl p-8 text-center">
              <Radio className="w-8 h-8 text-slate-700 mx-auto mb-3" />
              <p className="text-xs text-slate-600 font-mono">
                No compilation jobs yet.
                <br />
                Enter a script and instantiate the matrix.
              </p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[calc(100vh-14rem)] overflow-y-auto pr-1">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  isSelected={job.id === activeJobId}
                  onSelect={(id) => setActiveJobId(id)}
                  onDelete={(id) => deleteJob.mutate(id)}
                />
              ))}
            </div>
          )}

          {/* System diagnostics */}
          {config && (
            <div className="bg-[#0A0F1E] border border-[#1E293B] rounded-xl p-4 mt-4 space-y-2">
              <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">
                System Diagnostics
              </p>
              <DiagRow
                label="ffmpeg"
                value={config.ffmpeg_available ? "INSTALLED" : "MISSING"}
                ok={config.ffmpeg_available}
              />
              <DiagRow
                label="TTS endpoint"
                value="POLLINATIONS AI"
                ok={true}
              />
              <DiagRow
                label="API key"
                value={config.pollinations_api_key_set ? "CONFIGURED" : "FAIR-USE MODE"}
                ok={config.pollinations_api_key_set}
                warn={!config.pollinations_api_key_set}
              />
              <DiagRow
                label="voices"
                value={`${(config.voices || ALL_VOICES).length} channels`}
                ok={true}
              />
              <DiagRow
                label="concurrency"
                value="6 PARALLEL WORKERS"
                ok={true}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DiagRow({ label, value, ok, warn }) {
  return (
    <div className="flex items-center justify-between text-[10px] font-mono">
      <span className="text-slate-500 uppercase tracking-wider">{label}</span>
      <span
        className={`font-bold ${
          ok && !warn
            ? "text-emerald-400"
            : warn
            ? "text-amber-400"
            : "text-rose-400"
        }`}
      >
        {value}
      </span>
    </div>
  );
}
