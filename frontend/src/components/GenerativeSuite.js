/**
 * GenerativeSuite — $0 AI generation surface for the Video Studio.
 *
 * Surfaces:
 *   - Free-provider status (Pollinations always-on, HuggingFace if HF token set)
 *   - Image preview (Pollinations keyless, FLUX/turbo)
 *   - Voice clone reference upload (XTTS-v2 via HF)
 *   - AI background music prompt (MusicGen via HF) — passed through to render
 *
 * Returns selected `voice_ref_id` + `ai_music_prompt` to the parent so they
 * can be merged into the render payload.
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Wand2, Music2, Image as ImageIcon, UploadCloud, Mic, Loader2, Trash2, CheckCircle2, AlertTriangle, Sparkles } from "lucide-react";
import { videoAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

export function GenerativeSuite({ capability, voiceRefId, setVoiceRefId, aiMusicPrompt, setAiMusicPrompt, pollinationsVoice, setPollinationsVoice }) {
  const free = capability?.free_providers || {};
  const ttsVoices = capability?.pollinations_tts_voices || ["alloy", "echo", "fable", "onyx", "nova", "shimmer"];
  return (
    <div className="metric-card mb-6" data-testid="generative-suite">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Wand2 className="w-4 h-4 text-fuchsia-400" />
            <h3 className="text-base font-semibold text-white">Generative Suite</h3>
            <span className="text-[10px] uppercase tracking-wider text-fuchsia-300 bg-fuchsia-500/15 border border-fuchsia-500/30 rounded px-1.5 py-0.5">$0 / mo</span>
          </div>
          <p className="text-xs text-gray-500">
            Pollinations (keyless, image + TTS) + Hugging Face Inference (free FLUX-schnell image gen). All zero-cost.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-xs mb-4">
        <ProviderPill label="Pollinations" ok={!!free.pollinations_ai} note="keyless" />
        <ProviderPill label="Hugging Face" ok={!!free.huggingface} note={free.huggingface ? "FLUX-schnell" : "set HF token"} />
        <ProviderPill label="AI B-roll" ok={!!capability?.ai_b_roll_available} note={capability?.ai_b_roll_available ? "auto-on" : "—"} />
        <ProviderPill label="Pollinations TTS" ok={!!capability?.pollinations_tts_available} note="6 voices" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ImagePreview hfReady={!!free.huggingface} />
        <PollinationsTTSPanel voices={ttsVoices} pollinationsVoice={pollinationsVoice} setPollinationsVoice={setPollinationsVoice} />
        <VoiceRefPanel voiceRefId={voiceRefId} setVoiceRefId={setVoiceRefId} cloneAvailable={!!capability?.voice_cloning_available} />
      </div>

      {(capability?.ai_music_generation_available === false || capability?.text_to_video_available === false) && (
        <div className="mt-3 pt-3 border-t border-white/5">
          <p className="text-[10px] uppercase tracking-wider text-amber-300 mb-1">Free-tier notice (Feb 2026)</p>
          <p className="text-xs text-gray-400 leading-snug">
            Hugging Face pruned MusicGen, XTTS-v2 voice cloning, and AnimateDiff from the free hf-inference tier. The Generative Suite now uses <span className="text-emerald-300">Pollinations TTS</span> (keyless, 6 voices) for narration variety and the <span className="text-emerald-300">bundled CC0 music beds</span> for backing tracks. FLUX-schnell text-to-image still works free on HF.
          </p>
        </div>
      )}
    </div>
  );
}

function ProviderPill({ label, ok, note }) {
  return (
    <div className={`px-2.5 py-1.5 rounded border ${ok ? "bg-green-500/5 border-green-500/30 text-green-300" : "bg-amber-500/5 border-amber-500/30 text-amber-300"}`} data-testid={`gen-pill-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="flex items-center justify-between">
        <span className="font-medium">{label}</span>
        {ok ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
      </div>
      {note && <div className="text-[10px] mt-0.5 opacity-70">{note}</div>}
    </div>
  );
}

function ImagePreview({ hfReady }) {
  const [prompt, setPrompt] = useState("cinematic golden hour city skyline, neon highlights, 9:16 vertical");
  const [provider, setProvider] = useState("pollinations");
  const [dataUrl, setDataUrl] = useState(null);
  const gen = useMutation({
    mutationFn: () => videoAPI.generativeImage({ prompt, provider, width: 1024, height: 1024 }).then((r) => r.data),
    onSuccess: (data) => setDataUrl(data.data_url),
    onError: (e) => toast.error(e?.response?.data?.detail || e.message),
  });
  return (
    <div className="bg-[rgba(20,15,30,0.4)] border border-fuchsia-500/20 rounded-lg p-3" data-testid="generative-image-panel">
      <div className="text-[11px] font-semibold text-fuchsia-200 mb-2 flex items-center gap-1.5">
        <ImageIcon className="w-3.5 h-3.5" /> Image generation
      </div>
      <div className="flex gap-1 mb-2">
        <button
          type="button"
          onClick={() => setProvider("pollinations")}
          className={`flex-1 text-[10px] py-1 px-2 rounded border transition-colors ${provider === "pollinations" ? "border-fuchsia-400 bg-fuchsia-500/15 text-white" : "border-white/10 bg-black/20 text-gray-300"}`}
          data-testid="image-provider-pollinations"
        >Pollinations (turbo)</button>
        <button
          type="button"
          onClick={() => setProvider("huggingface")}
          disabled={!hfReady}
          className={`flex-1 text-[10px] py-1 px-2 rounded border transition-colors ${provider === "huggingface" ? "border-fuchsia-400 bg-fuchsia-500/15 text-white" : "border-white/10 bg-black/20 text-gray-300"} ${!hfReady ? "opacity-40 cursor-not-allowed" : ""}`}
          data-testid="image-provider-huggingface"
        >HF FLUX-schnell</button>
      </div>
      <Input
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe a 9:16 frame…"
        data-testid="generative-image-prompt"
        className="bg-black/30 border-white/10 text-xs h-8 mb-2"
      />
      <Button
        size="sm"
        onClick={() => gen.mutate()}
        disabled={gen.isPending || !prompt.trim()}
        className="w-full bg-fuchsia-600 hover:bg-fuchsia-700 text-xs h-8"
        data-testid="generative-image-btn"
      >
        {gen.isPending ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Sparkles className="w-3 h-3 mr-1" />}
        Generate {provider === "huggingface" ? "(~5s)" : "(~15s)"}
      </Button>
      {dataUrl && (
        <div className="mt-2">
          <img src={dataUrl} alt="ai preview" className="w-full rounded border border-white/10 aspect-square object-cover" data-testid="generative-image-result" />
        </div>
      )}
    </div>
  );
}

function PollinationsTTSPanel({ voices, pollinationsVoice, setPollinationsVoice }) {
  return (
    <div className="bg-[rgba(15,30,30,0.4)] border border-emerald-500/20 rounded-lg p-3" data-testid="pollinations-tts-panel">
      <div className="text-[11px] font-semibold text-emerald-200 mb-2 flex items-center gap-1.5">
        <Mic className="w-3.5 h-3.5" /> Narration voice (free, keyless)
      </div>
      <p className="text-[10px] text-gray-500 mb-2 leading-snug">
        OpenAI-compatible voices via Pollinations. Overrides Piper TTS when set.
      </p>
      <select
        value={pollinationsVoice}
        onChange={(e) => setPollinationsVoice(e.target.value)}
        className="w-full bg-black/30 border border-white/10 rounded px-2 py-1.5 text-xs text-white"
        data-testid="pollinations-voice-select"
      >
        <option value="">— Piper local (default) —</option>
        {(voices || []).map((v) => (
          <option key={v} value={v}>{v} (Pollinations)</option>
        ))}
      </select>
      {pollinationsVoice && (
        <div className="text-[10px] text-emerald-300/80 mt-2">
          Selected: <code className="text-emerald-200">{pollinationsVoice}</code>
        </div>
      )}
    </div>
  );
}

function VoiceRefPanel({ voiceRefId, setVoiceRefId, cloneAvailable }) {
  const queryClient = useQueryClient();
  const { data: refs = [] } = useQuery({
    queryKey: ["voice-refs"],
    queryFn: () => videoAPI.voiceRefs().then((r) => r.data),
  });
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const r = await videoAPI.uploadVoiceRef(file);
      setVoiceRefId(r.data.voice_ref_id);
      toast.success(`Voice reference uploaded: ${r.data.voice_ref_id}`);
      queryClient.invalidateQueries({ queryKey: ["voice-refs"] });
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await videoAPI.deleteVoiceRef(id);
      if (voiceRefId === id) setVoiceRefId("");
      queryClient.invalidateQueries({ queryKey: ["voice-refs"] });
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <div className="bg-[rgba(15,20,30,0.4)] border border-blue-500/20 rounded-lg p-3" data-testid="voice-clone-panel">
      <div className="text-[11px] font-semibold text-blue-200 mb-2 flex items-center gap-1.5">
        <UploadCloud className="w-3.5 h-3.5" /> Voice clone refs (XTTS-v2)
      </div>
      <p className="text-[10px] text-gray-500 mb-2 leading-snug">
        Upload 6-30s of clean speech.
        {!cloneAvailable && <span className="block text-amber-400 mt-1">Hosted XTTS-v2 unavailable on HF free tier (Feb 2026). Files saved for future local install.</span>}
      </p>
      <label className="block">
        <input
          type="file"
          accept="audio/*"
          onChange={handleUpload}
          disabled={uploading}
          className="hidden"
          data-testid="voice-ref-upload-input"
        />
        <span className={`block text-center text-xs py-2 px-3 rounded border border-dashed transition-colors cursor-pointer ${uploading ? "border-blue-400/30 bg-blue-500/5 text-blue-300/50" : "border-blue-400/40 bg-blue-500/5 hover:bg-blue-500/15 text-blue-200"}`}>
          {uploading ? <Loader2 className="w-3 h-3 inline animate-spin mr-1" /> : <UploadCloud className="w-3 h-3 inline mr-1" />}
          {uploading ? "Uploading…" : "Upload voice sample"}
        </span>
      </label>
      <div className="mt-2 max-h-32 overflow-y-auto space-y-1">
        {refs.length === 0 && (
          <p className="text-[10px] text-gray-500 italic">No voice refs yet</p>
        )}
        {refs.map((r) => (
          <label key={r.voice_ref_id} className="flex items-center gap-2 text-xs cursor-pointer" data-testid={`voice-ref-${r.voice_ref_id}`}>
            <input
              type="radio"
              name="voice-ref"
              checked={voiceRefId === r.voice_ref_id}
              onChange={() => setVoiceRefId(r.voice_ref_id)}
              className="accent-blue-400"
              disabled={!cloneAvailable}
            />
            <code className="text-blue-300 text-[10px] flex-1 truncate">{r.voice_ref_id}</code>
            <button onClick={(e) => { e.preventDefault(); handleDelete(r.voice_ref_id); }} className="text-red-400 hover:text-red-300">
              <Trash2 className="w-3 h-3" />
            </button>
          </label>
        ))}
        {voiceRefId && (
          <button
            onClick={() => setVoiceRefId("")}
            className="text-[10px] text-gray-400 hover:text-white"
            data-testid="voice-ref-clear"
          >
            Clear selection
          </button>
        )}
      </div>
    </div>
  );
}
