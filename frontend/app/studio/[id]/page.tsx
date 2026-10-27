"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Play,
  Film,
  Sparkles,
  RefreshCw,
  Clock,
  Layers,
  Volume2,
  Video,
  CheckCircle2,
  AlertCircle,
  Download,
} from "lucide-react";
import { api } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Generation, Project, Scene } from "@/types";

export default function VideoStudioPage() {
  const params = useParams();
  const projectId = params?.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [currentGeneration, setCurrentGeneration] = useState<Generation | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"storyboard" | "script" | "continuity">("storyboard");
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);
  const [generating, setGenerating] = useState(false);

  // Real-time WebSocket updates
  const { lastMessage } = useWebSocket(currentGeneration?.id);

  useEffect(() => {
    async function fetchStudioData() {
      try {
        const proj = await api.getProject(projectId);
        setProject(proj);

        // Fetch storyboard if available
        try {
          const sb = await api.generateStoryboard(projectId);
          setScenes(sb.scenes || []);
          if (sb.scenes && sb.scenes.length > 0) {
            setSelectedScene(sb.scenes[0]);
          }
        } catch {
          // No storyboard generated yet
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    if (projectId) {
      fetchStudioData();
    }
  }, [projectId]);

  // Sync WebSocket messages with generation state
  useEffect(() => {
    if (lastMessage && currentGeneration) {
      setCurrentGeneration((prev) =>
        prev
          ? {
              ...prev,
              status: lastMessage.status as any,
              progress_percent: lastMessage.progress,
              current_step: lastMessage.step,
              output_path: lastMessage.output_path || prev.output_path,
            }
          : null
      );
      if (lastMessage.status === "COMPLETED") {
        setGenerating(false);
      }
    }
  }, [lastMessage]);

  async function handleStartFullGeneration() {
    if (!project) return;
    setGenerating(true);
    try {
      const gen = await api.createGeneration(project.id, project.quality_mode);
      setCurrentGeneration(gen);
    } catch (err: any) {
      alert(`Failed to start generation: ${err.message}`);
      setGenerating(false);
    }
  }

  async function handleRegenerateScene(sceneId: string) {
    try {
      const updated = await api.generateStoryboard(projectId);
      setScenes(updated.scenes);
      alert("Scene regeneration requested.");
    } catch (err: any) {
      alert(`Regeneration failed: ${err.message}`);
    }
  }

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-400 text-sm">
        Loading Video Studio...
      </div>
    );
  }

  if (!project) {
    return (
      <div className="py-24 text-center text-red-400 text-sm">
        Project not found.
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-20">
      {/* Studio Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              {project.project_type}
            </span>
            <span className="text-xs text-slate-400">
              {project.target_duration}s • {project.aspect_ratio} • {project.quality_mode.toUpperCase()}
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            {project.name}
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleStartFullGeneration}
            disabled={generating}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-primary/25 transition"
          >
            {generating ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            <span>{generating ? "Rendering Video..." : "Generate Full Video"}</span>
          </button>
        </div>
      </div>

      {/* Live Generation Progress Bar if Active */}
      {currentGeneration && (
        <div className="p-4 rounded-xl bg-surface border border-blue-500/30 space-y-2 shadow-lg">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-white flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
              Status: {currentGeneration.status}
            </span>
            <span className="font-bold text-blue-400">
              {Math.round(currentGeneration.progress_percent)}%
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-surface-raised overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-600 to-cyan-400 transition-all duration-300"
              style={{ width: `${currentGeneration.progress_percent}%` }}
            />
          </div>
          <p className="text-[11px] text-slate-400">
            {currentGeneration.current_step || "Processing..."}
          </p>
        </div>
      )}

      {/* Studio Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Video Preview Player & Master Scene Detail */}
        <div className="lg:col-span-7 space-y-6">
          {/* Main Video Screen */}
          <div className="relative aspect-video rounded-2xl bg-black border border-border overflow-hidden flex items-center justify-center shadow-2xl">
            {project.output_path ? (
              <video
                src={project.output_path.replace("./storage/renders", "/renders")}
                controls
                className="w-full h-full object-contain"
              />
            ) : selectedScene?.video_path ? (
              <video
                src={selectedScene.video_path}
                controls
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-center p-8 space-y-3">
                <Video className="w-12 h-12 text-slate-600 mx-auto" />
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-slate-300">
                    {selectedScene ? selectedScene.title : "Timeline Ready"}
                  </p>
                  <p className="text-xs text-slate-500 max-w-xs mx-auto">
                    {generating
                      ? "Rendering scene clips with configured AI video provider..."
                      : "Click 'Generate Full Video' to assemble your scenes, narration, and subtitles."}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Scene Inspector */}
          {selectedScene && (
            <div className="p-5 rounded-2xl bg-surface border border-border space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <span className="text-[10px] uppercase font-bold text-accent-cyan tracking-wider">
                    Scene #{selectedScene.scene_number}
                  </span>
                  <h3 className="text-base font-bold text-white">
                    {selectedScene.title}
                  </h3>
                </div>
                <button
                  onClick={() => handleRegenerateScene(selectedScene.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-raised hover:bg-surface border border-border text-xs text-slate-300 font-medium transition"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Regenerate Scene</span>
                </button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-surface-raised border border-border">
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Shot Type</span>
                  <span className="text-white font-medium capitalize">{selectedScene.shot_type || "Medium"}</span>
                </div>
                <div className="p-3 rounded-lg bg-surface-raised border border-border">
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Camera Move</span>
                  <span className="text-white font-medium capitalize">{selectedScene.camera_movement || "Dolly Push"}</span>
                </div>
                <div className="p-3 rounded-lg bg-surface-raised border border-border">
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Duration</span>
                  <span className="text-white font-medium">{selectedScene.duration_seconds}s</span>
                </div>
                <div className="p-3 rounded-lg bg-surface-raised border border-border">
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Lighting</span>
                  <span className="text-white font-medium capitalize">{selectedScene.lighting || "Cinematic"}</span>
                </div>
              </div>

              {selectedScene.voice_over && (
                <div className="p-3.5 rounded-lg bg-surface-raised border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-accent-cyan tracking-wider flex items-center gap-1.5">
                    <Volume2 className="w-3.5 h-3.5" />
                    <span>Narration Script</span>
                  </span>
                  <p className="text-xs text-slate-300 leading-relaxed italic">
                    "{selectedScene.voice_over}"
                  </p>
                </div>
              )}

              <div className="space-y-1 text-xs">
                <span className="text-slate-400 font-semibold">Visual Prompt:</span>
                <p className="text-slate-300 p-3 rounded-lg bg-surface-raised border border-border text-[11px] leading-relaxed">
                  {selectedScene.video_prompt || selectedScene.image_prompt}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Right: Storyboard Timeline & Multi-Scene List */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Storyboard Scenes ({scenes.length})
            </h2>
            <span className="text-xs text-slate-400">
              Total {project.target_duration}s
            </span>
          </div>

          <div className="space-y-2.5 max-h-[720px] overflow-y-auto pr-1">
            {scenes.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 border border-dashed border-border rounded-xl">
                No scenes generated. Click "Generate Storyboard".
              </div>
            ) : (
              scenes.map((sc) => {
                const isSelected = selectedScene?.id === sc.id;
                return (
                  <div
                    key={sc.id}
                    onClick={() => setSelectedScene(sc)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
                      isSelected
                        ? "bg-blue-600/10 border-blue-500 shadow-md shadow-blue-500/10"
                        : "bg-surface border-border hover:bg-surface-raised"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 text-[10px] font-bold flex items-center justify-center">
                          {sc.scene_number}
                        </span>
                        <h4 className="text-xs font-bold text-white truncate max-w-[200px]">
                          {sc.title}
                        </h4>
                      </div>
                      <span className="text-[11px] text-slate-400 font-medium">
                        {sc.duration_seconds}s
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-2">
                      {sc.description || sc.video_prompt}
                    </p>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
