"use client";

import { useEffect, useState } from "react";
import { Mic, Play, Volume2, Globe, Sparkles, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

export default function VoiceStudioPage() {
  const [voices, setVoices] = useState<any[]>([]);
  const [languages, setLanguages] = useState<any[]>([]);
  const [testText, setTestText] = useState("Experience the extraordinary power of local artificial intelligence.");
  const [selectedLang, setSelectedLang] = useState("en");
  const [synthesizing, setSynthesizing] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [v, l] = await Promise.all([api.getVoices(), api.getLanguages()]);
        setVoices(v);
        setLanguages(l);
      } catch (err) {
        console.error(err);
      }
    }
    load();
  }, []);

  async function handlePreview() {
    if (!testText.trim()) return;
    setSynthesizing(true);
    setAudioUrl(null);

    try {
      const res = await api.previewVoice(testText, selectedLang);
      if (res.preview_path) {
        setAudioUrl(res.preview_path);
      }
    } catch (err: any) {
      alert(`Voice preview failed: ${err.message}`);
    } finally {
      setSynthesizing(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      <div className="border-b border-border pb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">
          Voice Studio & Multilingual Narration
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          High-fidelity text-to-speech with natural pacing, multi-accent modulation, and zero speech-speeding distortions.
        </p>
      </div>

      {/* Live Voice Synthesis Tester */}
      <div className="p-6 rounded-2xl bg-surface border border-border space-y-4 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-white">
          <Mic className="w-4 h-4 text-accent-cyan" />
          <span>Live Audio Narration Tester</span>
        </div>

        <div className="space-y-3">
          <textarea
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            rows={3}
            className="w-full rounded-xl bg-surface-raised border border-border p-3.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary resize-none"
            placeholder="Type sample narration script to test..."
          />

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">Language:</span>
              <select
                value={selectedLang}
                onChange={(e) => setSelectedLang(e.target.value)}
                className="rounded-lg bg-surface-raised border border-border px-3 py-1.5 text-slate-200 text-xs"
              >
                {languages.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handlePreview}
              disabled={synthesizing}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 text-white text-xs font-bold transition shadow-md shadow-primary/20"
            >
              <Volume2 className="w-4 h-4" />
              <span>{synthesizing ? "Synthesizing Speech..." : "Test Voice Preview"}</span>
            </button>
          </div>

          {audioUrl && (
            <div className="p-3 rounded-xl bg-surface-raised border border-emerald-500/30 flex items-center justify-between text-xs">
              <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>Audio Rendered Successfully</span>
              </span>
              <span className="text-slate-400 text-[11px] truncate max-w-xs font-mono">
                {audioUrl}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Preset Voices Grid */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-white">Preset Voice Profiles</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {voices.map((v) => (
            <div key={v.id} className="p-5 rounded-xl bg-surface border border-border space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  {v.gender} • {v.language.toUpperCase()}
                </span>
                <span className="text-xs text-slate-500 font-medium">{v.style}</span>
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">{v.name}</h3>
                <p className="text-xs text-slate-400 mt-1">Native hardware engine synthesis</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
