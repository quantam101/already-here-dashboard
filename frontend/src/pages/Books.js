import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Plus, Download, Play, Pause, Trash2, FileText, Headphones, AlertTriangle } from "lucide-react";
import { booksAPI, systemAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";

const BOOK_TYPES = ["ebook", "manual", "journal", "workbook", "guide", "memoir"];
const TONES = ["professional", "conversational", "inspirational", "technical"];

const INITIAL = {
  title: "", book_type: "ebook", audience: "general operators",
  tone: "professional", chapter_count: 6, word_target_per_chapter: 800,
  outline_hints: "",
};

function NewBookDialog() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(INITIAL);

  const create = useMutation({
    mutationFn: (payload) => booksAPI.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["books"] });
      queryClient.invalidateQueries({ queryKey: ["bookStats"] });
      toast.success("Book generated and saved");
      setOpen(false);
      setForm(INITIAL);
    },
    onError: (err) => toast.error(err?.response?.data?.detail || err.message),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.title.trim()) return toast.error("Title required");
    create.mutate({
      title: form.title.trim(),
      book_type: form.book_type,
      audience: form.audience,
      tone: form.tone,
      chapter_count: parseInt(form.chapter_count, 10) || 6,
      word_target_per_chapter: parseInt(form.word_target_per_chapter, 10) || 800,
      outline_hints: form.outline_hints.split("\n").map((s) => s.trim()).filter(Boolean),
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-green-600 hover:bg-green-700 text-white" data-testid="book-create-trigger">
          <Plus className="w-4 h-4 mr-1.5" /> Generate Book
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#0f1419] border-white/10 text-white max-w-lg">
        <DialogHeader>
          <DialogTitle>Generate a Book / Manual / Journal</DialogTitle>
          <DialogDescription className="text-gray-400 text-sm">
            Chapter-by-chapter generation via Gemini 3 Flash. $0 cost. ~30-90s.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3" data-testid="book-create-form">
          <div>
            <Label>Title</Label>
            <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white" data-testid="book-title" required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Type</Label>
              <select value={form.book_type} onChange={(e) => setForm({ ...form, book_type: e.target.value })}
                className="mt-1 w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
                data-testid="book-type">
                {BOOK_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <Label>Tone</Label>
              <select value={form.tone} onChange={(e) => setForm({ ...form, tone: e.target.value })}
                className="mt-1 w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2">
                {TONES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div>
            <Label>Target Audience</Label>
            <Input value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Chapters</Label>
              <Input type="number" min="1" max="20" value={form.chapter_count}
                onChange={(e) => setForm({ ...form, chapter_count: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white" data-testid="book-chapters" />
            </div>
            <div>
              <Label>Words / Chapter</Label>
              <Input type="number" min="100" max="3000" value={form.word_target_per_chapter}
                onChange={(e) => setForm({ ...form, word_target_per_chapter: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white" />
            </div>
          </div>
          <div>
            <Label>Outline Hints (one per line, optional)</Label>
            <textarea value={form.outline_hints} rows="3"
              onChange={(e) => setForm({ ...form, outline_hints: e.target.value })}
              className="w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
              placeholder="- focus on agentic AI&#10;- include case studies" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={create.isPending}
              className="bg-green-600 hover:bg-green-700 text-white" data-testid="book-create-submit">
              {create.isPending ? "Generating..." : "Generate"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function AudioBookPlayer({ book }) {
  const [mode, setMode] = useState("server"); // server | browser
  const [serverState, setServerState] = useState("idle"); // idle | rendering | ready | failed
  const [browserPlaying, setBrowserPlaying] = useState(false);
  const utterRef = useRef(null);
  const mp3Url = booksAPI.downloadMp3(book.id);

  useEffect(() => () => window.speechSynthesis?.cancel(), []);

  // Poll the MP3 url every 5s until it returns 200, then unlock the <audio> element.
  useEffect(() => {
    if (mode !== "server" || serverState === "ready") return undefined;
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await fetch(mp3Url, { method: "HEAD" });
        if (cancelled) return;
        if (r.status === 200) setServerState("ready");
        else if (r.status === 202) setServerState("rendering");
        else setServerState("failed");
      } catch {
        if (!cancelled) setServerState("failed");
      }
    };
    tick();
    const handle = window.setInterval(tick, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, [mode, serverState, mp3Url]);

  const playBrowser = () => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      toast.error("Your browser does not support speech synthesis");
      return;
    }
    window.speechSynthesis.cancel();
    const lines = [book.title + "."];
    (book.chapters || []).forEach((c) => {
      lines.push(`Chapter ${c.number}. ${c.title}.`);
      lines.push(c.content.replace(/[#*_`]/g, ""));
    });
    const text = lines.join(" ");
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.05;
    u.onend = () => setBrowserPlaying(false);
    u.onerror = () => setBrowserPlaying(false);
    utterRef.current = u;
    window.speechSynthesis.speak(u);
    setBrowserPlaying(true);
  };

  const stopBrowser = () => {
    window.speechSynthesis?.cancel();
    setBrowserPlaying(false);
  };

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid={`audio-${book.id}`}>
      {mode === "server" ? (
        <>
          {serverState === "ready" ? (
            <>
              <audio
                controls
                src={mp3Url}
                preload="none"
                className="h-9 max-w-[260px]"
                data-testid={`audio-mp3-${book.id}`}
              />
              <a
                href={mp3Url}
                download={`${book.title.replace(/\s+/g, "_").slice(0, 60)}.mp3`}
                className="text-xs text-purple-300 hover:text-purple-200 underline"
                data-testid={`audio-download-${book.id}`}
              >
                Download MP3
              </a>
            </>
          ) : serverState === "rendering" ? (
            <span className="text-xs text-amber-300 flex items-center gap-1.5" data-testid={`audio-rendering-${book.id}`}>
              <Headphones className="w-3 h-3 animate-pulse" /> Audiobook rendering... ~30-60s per chapter
            </span>
          ) : serverState === "failed" ? (
            <span className="text-xs text-red-400">MP3 render failed — try browser voice fallback</span>
          ) : (
            <span className="text-xs text-gray-400">checking audiobook...</span>
          )}
          <button
            type="button"
            onClick={() => setMode("browser")}
            className="text-[10px] text-gray-500 hover:text-gray-300 underline"
            data-testid={`audio-fallback-${book.id}`}
          >
            use browser voice
          </button>
        </>
      ) : (
        <>
          <Button
            size="sm"
            variant="outline"
            onClick={browserPlaying ? stopBrowser : playBrowser}
            className="border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
            data-testid={`audio-browser-btn-${book.id}`}
          >
            {browserPlaying ? (
              <><Pause className="w-3.5 h-3.5 mr-1" /> Stop</>
            ) : (
              <><Play className="w-3.5 h-3.5 mr-1" /> Browser TTS</>
            )}
          </Button>
          <button
            type="button"
            onClick={() => setMode("server")}
            className="text-[10px] text-gray-500 hover:text-gray-300 underline"
          >
            back to MP3
          </button>
        </>
      )}
    </div>
  );
}

function BookCard({ book, onDelete }) {
  const downloadMd = booksAPI.downloadMd(book.id);
  const downloadTxt = booksAPI.downloadTxt(book.id);
  return (
    <div
      className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-xl p-5 hover:border-green-500/30 transition-colors"
      data-testid={`book-${book.id}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <BookOpen className="w-5 h-5 text-green-400 shrink-0" />
            <h4 className="text-base font-semibold text-white truncate">{book.title}</h4>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="content-badge bg-blue-500/15 text-blue-300 border border-blue-500/20">
              {book.book_type}
            </span>
            <span className={`content-badge status-badge-${book.status === "complete" ? "active" : book.status === "failed" ? "failed" : "pending"}`}>
              {book.status}
            </span>
            <span className="text-xs text-gray-500">{book.chapters?.length || 0} chapters · {book.total_word_count?.toLocaleString()} words</span>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={() => onDelete(book.id)}
          className="text-gray-400 hover:text-red-400 hover:bg-red-500/10 shrink-0"
          data-testid={`book-delete-${book.id}`}>
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
      {book.chapters?.[0] && (
        <p className="text-xs text-gray-400 mb-4 line-clamp-2">{book.chapters[0].content.slice(0, 240)}...</p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button asChild size="sm" variant="outline" className="border-blue-500/30 text-blue-300 hover:bg-blue-500/10">
          <a href={downloadMd} download data-testid={`download-md-${book.id}`}>
            <Download className="w-3.5 h-3.5 mr-1" /> .md
          </a>
        </Button>
        <Button asChild size="sm" variant="outline" className="border-green-500/30 text-green-300 hover:bg-green-500/10">
          <a href={downloadTxt} download data-testid={`download-txt-${book.id}`}>
            <FileText className="w-3.5 h-3.5 mr-1" /> .txt
          </a>
        </Button>
        <AudioBookPlayer book={book} />
      </div>
    </div>
  );
}

export default function Books() {
  const queryClient = useQueryClient();
  const { data: books = [] } = useQuery({
    queryKey: ["books"],
    queryFn: () => booksAPI.getAll().then((r) => r.data),
  });
  const { data: stats } = useQuery({
    queryKey: ["bookStats"],
    queryFn: () => booksAPI.stats().then((r) => r.data),
  });
  const { data: sysStatus } = useQuery({
    queryKey: ["system-status-books"],
    queryFn: () => systemAPI.status().then((r) => r.data),
    refetchInterval: 60000,
  });
  const del = useMutation({
    mutationFn: (id) => booksAPI.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["books"] });
      queryClient.invalidateQueries({ queryKey: ["bookStats"] });
      toast.success("Book deleted");
    },
  });

  const tiles = [
    { label: "Books", value: stats?.total_books || 0, accent: "text-green-400" },
    { label: "Total Words", value: (stats?.total_word_count || 0).toLocaleString(), accent: "text-blue-400" },
    { label: "Downloads", value: stats?.total_downloads || 0, accent: "text-purple-400" },
    { label: "Audiobook-Ready", value: books.filter((b) => b.status === "complete").length, accent: "text-yellow-400" },
  ];

  return (
    <div data-testid="books-page" className="p-6 dark-themed-page space-y-6">
      {sysStatus?.llm_mock_mode && (
        <div
          className="bg-amber-500/10 border border-amber-500/40 rounded-lg p-3 flex items-start gap-3"
          data-testid="llm-mock-banner"
        >
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold text-amber-200">LLM is in MOCK MODE — books will contain placeholder text.</p>
            <p className="text-amber-200/80 text-xs mt-1 leading-relaxed">
              Your <code className="bg-black/40 px-1 py-0.5 rounded">LLM_API_KEY</code> in <code>backend/.env</code> is a placeholder
              (<code>sk-mock-…</code> or <code>sk-emergent-…</code>). Real content needs a real provider key.
              Swap it for a Google AI Studio (free tier), Anthropic, or OpenAI key and restart the backend.
              Audiobook MP3 generation also works in mock mode — the placeholder text will just be read aloud.
            </p>
          </div>
        </div>
      )}
      <div className="page-header flex items-center justify-between gap-4">
        <div>
          <h1>Books & Audiobooks</h1>
          <p>AI-generated books, manuals, journals — sell as PDF/EPUB on Amazon KDP, Gumroad, direct.</p>
        </div>
        <NewBookDialog />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {tiles.map((t) => (
          <div key={t.label} className="stat-card">
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">{t.label}</p>
            <p className={`text-3xl font-bold ${t.accent}`}>{t.value}</p>
          </div>
        ))}
      </div>

      <div className="metric-card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Headphones className="w-5 h-5 text-purple-400" /> Library
          </h3>
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
            {books.length} BOOKS
          </span>
        </div>
        {books.length === 0 ? (
          <div className="text-center py-12">
            <BookOpen className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-300 mb-2">No books yet</p>
            <p className="text-sm text-gray-500">
              Click <span className="text-green-400 font-medium">Generate Book</span> to create your first ebook or manual.
              Each book becomes a sellable asset under the <span className="text-blue-400">rev-books</span> stream.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="books-list">
            {books.map((b) => <BookCard key={b.id} book={b} onDelete={del.mutate} />)}
          </div>
        )}
      </div>
    </div>
  );
}
