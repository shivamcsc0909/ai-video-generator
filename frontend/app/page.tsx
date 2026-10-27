"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Film,
  PlusCircle,
  Play,
  Clock,
  Sparkles,
  Layers,
  Cpu,
  ArrowRight,
  HardDrive,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";
import { HardwareInfo, Project } from "@/types";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [stats, setStats] = useState<{ total_projects: number; total_generations: number } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [projData, hwData, statData] = await Promise.all([
          api.getProjects(),
          api.getHardware(),
          api.getSystemStats(),
        ]);
        setProjects(projData.items);
        setHardware(hwData);
        setStats(statData);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Hero Quick Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-900/40 via-surface to-surface-raised border border-border p-8 shadow-xl">
        <div className="relative z-10 max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Local-First AI Video Production</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
            Create Studio-Grade Videos Directly on Your Mac
          </h1>
          <p className="text-slate-400 text-sm leading-relaxed">
            Multi-scene storyboarding, character continuity, synchronized voiceover,
            burned subtitles, and seamless multi-account API rotation.
          </p>
          <div className="pt-2 flex items-center gap-4">
            <Link
              href="/new"
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white text-sm font-semibold shadow-lg shadow-blue-500/25 transition"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Create New Video</span>
            </Link>
            <Link
              href="/settings/providers"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-surface-raised hover:bg-surface border border-border text-slate-300 text-sm font-medium transition"
            >
              <span>Manage AI Providers</span>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </Link>
          </div>
        </div>
      </div>

      {/* Hardware & System Telemetry Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-surface border border-border space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Hardware Target</span>
            <Cpu className="w-4 h-4 text-accent-cyan" />
          </div>
          <div className="text-xl font-bold text-white">
            {hardware ? (hardware.is_apple_silicon ? "Apple Silicon" : hardware.cpu_model) : "Detecting..."}
          </div>
          <p className="text-xs text-slate-500">
            {hardware ? `${hardware.ram_gb} GB Unified Memory` : "Checking unified memory..."}
          </p>
        </div>

        <div className="p-5 rounded-xl bg-surface border border-border space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Media Engine (FFmpeg)</span>
            <Film className="w-4 h-4 text-accent-emerald" />
          </div>
          <div className="text-xl font-bold text-white flex items-center gap-2">
            {hardware?.ffmpeg_available ? (
              <>
                <CheckCircle2 className="w-5 h-5 text-accent-emerald" />
                <span>Installed</span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-5 h-5 text-accent-amber" />
                <span>Python Engine</span>
              </>
            )}
          </div>
          <p className="text-xs text-slate-500 truncate">
            {hardware?.ffmpeg_version ? `Version: ${hardware.ffmpeg_version}` : "Ready for audio/video stitching"}
          </p>
        </div>

        <div className="p-5 rounded-xl bg-surface border border-border space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total Projects</span>
            <Layers className="w-4 h-4 text-accent-violet" />
          </div>
          <div className="text-xl font-bold text-white">
            {stats ? stats.total_projects : projects.length}
          </div>
          <p className="text-xs text-slate-500">Saved in local storage</p>
        </div>

        <div className="p-5 rounded-xl bg-surface border border-border space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Available Storage</span>
            <HardDrive className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-xl font-bold text-white">
            {hardware ? `${hardware.available_disk_gb} GB` : "50+ GB"}
          </div>
          <p className="text-xs text-slate-500">Local project storage</p>
        </div>
      </div>

      {/* Projects Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Recent Video Projects</h2>
            <p className="text-xs text-slate-400">
              Your generated timelines, scene storyboards, and exported renders
            </p>
          </div>
          <Link
            href="/new"
            className="flex items-center gap-1.5 text-xs font-semibold text-primary hover:text-primary-light"
          >
            <span>+ Create New</span>
          </Link>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-500 text-sm">
            Loading video studio projects...
          </div>
        ) : projects.length === 0 ? (
          <div className="py-16 border border-dashed border-border rounded-2xl text-center space-y-4 bg-surface/40">
            <Film className="w-12 h-12 text-slate-600 mx-auto" />
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-white">No projects created yet</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Generate an advertisement, architectural walkthrough, product demo, or explainer video.
              </p>
            </div>
            <Link
              href="/new"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white text-xs font-semibold hover:bg-primary-hover transition"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Create Your First Video</span>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {projects.map((proj) => (
              <Link
                key={proj.id}
                href={`/studio/${proj.id}`}
                className="group rounded-xl bg-surface border border-border hover:border-blue-500/50 transition-all p-5 flex flex-col justify-between space-y-4 hover:shadow-lg hover:shadow-blue-500/5"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-semibold border border-blue-500/20">
                      {proj.project_type}
                    </span>
                    <span className="text-xs text-slate-500">
                      {proj.target_duration}s • {proj.aspect_ratio}
                    </span>
                  </div>
                  <h3 className="font-bold text-base text-white group-hover:text-blue-400 transition truncate">
                    {proj.name}
                  </h3>
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {proj.prompt}
                  </p>
                </div>

                <div className="pt-3 border-t border-border flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{new Date(proj.created_at).toLocaleDateString()}</span>
                  </span>
                  <span className="flex items-center gap-1 text-primary font-medium group-hover:translate-x-0.5 transition-transform">
                    <span>Open Studio</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
