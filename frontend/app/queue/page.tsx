"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Clock,
  Play,
  RotateCcw,
  XCircle,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Layers,
} from "lucide-react";
import { api } from "@/lib/api";
import { Generation, Project } from "@/types";

export default function RenderQueuePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getProjects();
        setProjects(data.items);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-16">
      <div className="flex items-center justify-between border-b border-border pb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Render Queue & Background Jobs
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time pipeline monitoring, scene processing stages, and error recovery.
          </p>
        </div>
      </div>

      <div className="rounded-2xl bg-surface border border-border overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-20 text-center text-slate-500 text-sm">
            Loading render queue...
          </div>
        ) : projects.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-xs italic">
            No active or queued video generation jobs.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-raised/80 text-slate-400 font-semibold border-b border-border uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-3 px-4">Project</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {projects.map((proj) => (
                  <tr key={proj.id} className="hover:bg-surface-raised/40 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-white truncate max-w-xs">
                        {proj.name}
                      </div>
                      <div className="text-[11px] text-slate-500 truncate max-w-xs">
                        {proj.prompt}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-semibold uppercase">
                        {proj.project_type}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-300 font-medium">
                      {proj.target_duration}s ({proj.aspect_ratio})
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-semibold">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Ready in Studio</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">
                      {new Date(proj.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        href={`/studio/${proj.id}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-raised hover:bg-background border border-border text-primary font-medium transition"
                      >
                        <span>Open Studio</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
