"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  Upload,
  Sliders,
  ChevronDown,
  ChevronUp,
  Volume2,
  Film,
  Clock,
  Layers,
  Shield,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { AspectRatio, ProjectType, QualityMode } from "@/types";

export default function NewVideoPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [name, setName] = useState("");
  const [projectType, setProjectType] = useState<ProjectType>("advertisement");
  const [duration, setDuration] = useState<number>(60);
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>("16:9");
  const [qualityMode, setQualityMode] = useState<QualityMode>("balanced");
  const [voiceLang, setVoiceLang] = useState("en");
  const [voiceName, setVoiceName] = useState("Samantha");
  const [voiceEmotion, setVoiceEmotion] = useState("Confident");
  const [subtitles, setSubtitles] = useState(true);
  const [music, setMusic] = useState(true);
  const [sfx, setSfx] = useState(true);
  const [watermark, setWatermark] = useState(false);

  // Advanced mode
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [negativePrompt, setNegativePrompt] = useState("");
  const [cameraMove, setCameraMove] = useState("cinematic");
  const [fps, setFps] = useState(24);
  const [seed, setSeed] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const durationOptions = [
    { label: "30 seconds", val: 30 },
    { label: "45 seconds", val: 45 },
    { label: "60 seconds", val: 60 },
    { label: "90 seconds", val: 90 },
    { label: "2 minutes", val: 120 },
    { label: "3 minutes", val: 180 },
    { label: "5 minutes", val: 300 },
  ];

  const aspectOptions: { label: string; ratio: AspectRatio; desc: string }[] = [
    { label: "Landscape", ratio: "16:9", desc: "YouTube / Web" },
    { label: "Social", ratio: "9:16", desc: "TikTok / Reels / Shorts" },
    { label: "Square", ratio: "1:1", desc: "Feed Posts" },
    { label: "Portrait", ratio: "4:5", desc: "Instagram" },
  ];

  const qualityOptions: { mode: QualityMode; title: string; desc: string }[] = [
    { mode: "local", title: "Free / Local", desc: "100% on device, zero API cost" },
    { mode: "balanced", title: "Balanced", desc: "Local-first with free cloud fallback" },
    { mode: "quality", title: "High Quality", desc: "Premium models within budget limits" },
    { mode: "max_quality", title: "Max Quality", desc: "Highest-fidelity configured models" },
  ];

  const videoTypes: { type: ProjectType; label: string }[] = [
    { type: "advertisement", label: "Commercial Ad" },
    { type: "product", label: "Product Showcase" },
    { type: "architecture", label: "Architecture / Penthouse" },
    { type: "engineering", label: "Exploded Assembly" },
    { type: "cartoon", label: "Cartoon / Character" },
    { type: "educational", label: "Explainer / Educational" },
    { type: "social_media", label: "Social Media Reel" },
    { type: "documentary", label: "Documentary Style" },
  ];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) {
      setError("Please provide a prompt describing your video.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Auto-generate a title if none provided
      const projName = name.trim() || `${projectType.toUpperCase()}: ${prompt.slice(0, 35)}...`;

      const newProj = await api.createProject({
        name: projName,
        prompt: prompt.trim(),
        project_type: projectType,
        target_duration: duration,
        aspect_ratio: aspectRatio,
        quality_mode: qualityMode,
        voice_language: voiceLang,
        voice_name: voiceName,
        voice_emotion: voiceEmotion,
        include_subtitles: subtitles,
        include_music: music,
        include_sfx: sfx,
        settings: {
          fps,
          negative_prompt: negativePrompt,
          camera_movement: cameraMove,
          seed: seed ? parseInt(seed) : undefined,
          watermark,
        },
      });

      // Automatically generate initial storyboard & redirect to studio
      router.push(`/studio/${newProj.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create project.");
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">
          What do you want to create?
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Provide your text prompt, script, or instructions. The studio will break it down into scenes, voice narration, and cinematic visual clips.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Main Prompt Box */}
        <div className="space-y-2">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
            Prompt / Script / Video Concept <span className="text-red-400">*</span>
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={5}
            placeholder="e.g. Create a 60-second cinematic advertisement for a luxury penthouse with floor-to-ceiling glass, marble kitchen, sunset balcony views, and confident commercial voiceover..."
            className="w-full rounded-xl bg-surface border border-border p-4 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition resize-none leading-relaxed"
            required
          />
        </div>

        {/* Video Type Preset Selection */}
        <div className="space-y-2">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
            Video Type
          </label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
            {videoTypes.map((t) => (
              <button
                type="button"
                key={t.type}
                onClick={() => setProjectType(t.type)}
                className={`p-3 rounded-lg text-left text-xs font-medium border transition-all ${
                  projectType === t.type
                    ? "bg-primary/10 border-primary text-primary-light shadow-sm"
                    : "bg-surface border-border text-slate-400 hover:text-slate-200 hover:bg-surface-raised"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Runtime & Aspect Ratio */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Target Runtime */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Target Duration
            </label>
            <select
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full rounded-lg bg-surface border border-border px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-primary"
            >
              {durationOptions.map((opt) => (
                <option key={opt.val} value={opt.val}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Aspect Ratio */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Aspect Ratio
            </label>
            <div className="grid grid-cols-2 gap-2">
              {aspectOptions.map((opt) => (
                <button
                  type="button"
                  key={opt.ratio}
                  onClick={() => setAspectRatio(opt.ratio)}
                  className={`p-2.5 rounded-lg border text-left text-xs transition ${
                    aspectRatio === opt.ratio
                      ? "bg-primary/10 border-primary text-primary-light"
                      : "bg-surface border-border text-slate-400 hover:bg-surface-raised"
                  }`}
                >
                  <div className="font-semibold text-white">{opt.ratio}</div>
                  <div className="text-[10px] text-slate-500 truncate">{opt.desc}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Smart Quality Modes */}
        <div className="space-y-2">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
            Quality Mode
          </label>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {qualityOptions.map((opt) => (
              <button
                type="button"
                key={opt.mode}
                onClick={() => setQualityMode(opt.mode)}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  qualityMode === opt.mode
                    ? "bg-blue-600/10 border-blue-500 text-blue-300 shadow-md shadow-blue-500/10"
                    : "bg-surface border-border text-slate-400 hover:bg-surface-raised"
                }`}
              >
                <div className="text-xs font-bold text-white">{opt.title}</div>
                <div className="text-[11px] text-slate-500 mt-1 leading-snug">
                  {opt.desc}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Voice Narration Settings */}
        <div className="p-5 rounded-xl bg-surface border border-border space-y-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-white">
            <Volume2 className="w-4 h-4 text-accent-cyan" />
            <span>Voice & Narration</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="block text-slate-400 mb-1">Language</label>
              <select
                value={voiceLang}
                onChange={(e) => setVoiceLang(e.target.value)}
                className="w-full rounded-lg bg-surface-raised border border-border px-3 py-2 text-slate-200"
              >
                <option value="en">English (US/UK/IN)</option>
                <option value="hi">Hindi (हिंदी)</option>
                <option value="hinglish">Hinglish</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="ja">Japanese</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Voice Profile</label>
              <select
                value={voiceName}
                onChange={(e) => setVoiceName(e.target.value)}
                className="w-full rounded-lg bg-surface-raised border border-border px-3 py-2 text-slate-200"
              >
                <option value="Samantha">Samantha (American Female)</option>
                <option value="Daniel">Daniel (British Male)</option>
                <option value="Rishi">Rishi (Indian English Male)</option>
                <option value="Lekha">Lekha (Hindi Female)</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Narration Emotion</label>
              <select
                value={voiceEmotion}
                onChange={(e) => setVoiceEmotion(e.target.value)}
                className="w-full rounded-lg bg-surface-raised border border-border px-3 py-2 text-slate-200"
              >
                <option value="Confident">Confident Commercial</option>
                <option value="Warm">Warm & Welcoming</option>
                <option value="Energetic">Energetic & Punchy</option>
                <option value="Formal">Documentary Formal</option>
              </select>
            </div>
          </div>
        </div>

        {/* Audio & Media Layer Switches */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <label className="flex items-center gap-2.5 p-3 rounded-lg bg-surface border border-border cursor-pointer hover:bg-surface-raised transition text-xs font-medium text-slate-300">
            <input
              type="checkbox"
              checked={subtitles}
              onChange={(e) => setSubtitles(e.target.checked)}
              className="rounded bg-surface-raised border-border text-primary focus:ring-0"
            />
            <span>Burned Subtitles</span>
          </label>

          <label className="flex items-center gap-2.5 p-3 rounded-lg bg-surface border border-border cursor-pointer hover:bg-surface-raised transition text-xs font-medium text-slate-300">
            <input
              type="checkbox"
              checked={music}
              onChange={(e) => setMusic(e.target.checked)}
              className="rounded bg-surface-raised border-border text-primary focus:ring-0"
            />
            <span>Background Music</span>
          </label>

          <label className="flex items-center gap-2.5 p-3 rounded-lg bg-surface border border-border cursor-pointer hover:bg-surface-raised transition text-xs font-medium text-slate-300">
            <input
              type="checkbox"
              checked={sfx}
              onChange={(e) => setSfx(e.target.checked)}
              className="rounded bg-surface-raised border-border text-primary focus:ring-0"
            />
            <span>Sound Effects (SFX)</span>
          </label>

          <label className="flex items-center gap-2.5 p-3 rounded-lg bg-surface border border-border cursor-pointer hover:bg-surface-raised transition text-xs font-medium text-slate-300">
            <input
              type="checkbox"
              checked={watermark}
              onChange={(e) => setWatermark(e.target.checked)}
              className="rounded bg-surface-raised border-border text-primary focus:ring-0"
            />
            <span>Brand Watermark</span>
          </label>
        </div>

        {/* Collapsible Advanced Settings */}
        <div className="border border-border rounded-xl overflow-hidden bg-surface">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full flex items-center justify-between p-4 text-xs font-semibold text-slate-300 hover:bg-surface-raised transition"
          >
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-primary" />
              <span>Advanced Studio Controls (FPS, Negative Prompt, Camera Motion, Seed)</span>
            </div>
            {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showAdvanced && (
            <div className="p-4 border-t border-border space-y-4 text-xs bg-surface-raised/50">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-slate-400 mb-1">Target FPS</label>
                  <select
                    value={fps}
                    onChange={(e) => setFps(Number(e.target.value))}
                    className="w-full rounded bg-surface border border-border px-3 py-2 text-slate-200"
                  >
                    <option value={24}>24 fps (Cinematic)</option>
                    <option value={30}>30 fps (Standard)</option>
                    <option value={60}>60 fps (Smooth Motion)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Default Camera Language</label>
                  <select
                    value={cameraMove}
                    onChange={(e) => setCameraMove(e.target.value)}
                    className="w-full rounded bg-surface border border-border px-3 py-2 text-slate-200"
                  >
                    <option value="cinematic">Cinematic Dolly & Push</option>
                    <option value="drone">Aerial Drone Flythrough</option>
                    <option value="orbit">360° Subject Orbit</option>
                    <option value="static">Tripod Static</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Fixed Seed (Optional)</label>
                  <input
                    type="number"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    placeholder="Random by default"
                    className="w-full rounded bg-surface border border-border px-3 py-2 text-slate-200"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Negative Prompt</label>
                <input
                  type="text"
                  value={negativePrompt}
                  onChange={(e) => setNegativePrompt(e.target.value)}
                  placeholder="blurry, distorted geometry, low quality, artifacts, watermark"
                  className="w-full rounded bg-surface border border-border px-3 py-2 text-slate-200"
                />
              </div>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 text-white font-bold text-sm shadow-xl shadow-primary/25 transition flex items-center justify-center gap-2"
          >
            {loading ? (
              <span>Planning Storyboard...</span>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>GENERATE VIDEO</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
