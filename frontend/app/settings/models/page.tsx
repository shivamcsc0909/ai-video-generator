"use client";

import { useEffect, useState } from "react";
import { Cpu, CheckCircle2, ShieldCheck, Zap } from "lucide-react";
import { api } from "@/lib/api";

export default function ModelRegistryPage() {
  const models = [
    { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro", provider: "Google Gemini", type: "LLM Script & Storyboard", speed: "Fast", cost: "Free / Cloud" },
    { id: "llama-3.1-70b", name: "Llama 3.1 70B (Groq)", provider: "Groq", type: "LLM Instant Inference", speed: "Instant", cost: "Free Tier" },
    { id: "comfyui-animatediff", name: "AnimateDiff V3", provider: "Local ComfyUI", type: "Local Video Generation", speed: "Medium (MPS)", cost: "100% Free / Local" },
    { id: "svd-xt", name: "Stable Video Diffusion XT", provider: "Local / Fal", type: "Image-to-Video", speed: "Medium", cost: "Local / Cloud" },
    { id: "kling-video", name: "Kling Video V1", provider: "Fal.ai", type: "Cinematic High-Motion", speed: "Fast (Queue)", cost: "Per-second" },
    { id: "wan-2.1-1.3b", name: "Wan 2.1 1.3B", provider: "Replicate / Fal", type: "Next-Gen Diffusion Video", speed: "Fast", cost: "Per-second" },
    { id: "flux-schnell", name: "FLUX.1 Schnell", provider: "Hugging Face / Fal", type: "Master Keyframe Image", speed: "Ultra-fast", cost: "Free / Cloud" },
    { id: "whisper-v3", name: "Whisper Large V3", provider: "Local / Groq", type: "Subtitles & Transcription", speed: "Realtime", cost: "Free" },
    { id: "eleven-multilingual-v2", name: "Eleven Multilingual V2", provider: "ElevenLabs", type: "Expressive Voice Synthesis", speed: "Fast", cost: "Per-character" },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-16">
      <div className="border-b border-border pb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">
          AI Model Registry
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Catalog of video, image, voice, transcription, and reasoning models supported by the studio.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {models.map((m) => (
          <div key={m.id} className="p-5 rounded-xl bg-surface border border-border space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                {m.provider}
              </span>
              <span className="text-[10px] text-slate-500 font-medium">
                {m.cost}
              </span>
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">{m.name}</h3>
              <p className="text-xs text-slate-400 mt-0.5">{m.type}</p>
            </div>
            <div className="pt-2 border-t border-border flex items-center justify-between text-[11px] text-slate-500">
              <span>Speed: {m.speed}</span>
              <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                <CheckCircle2 className="w-3 h-3" />
                <span>Compatible</span>
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
