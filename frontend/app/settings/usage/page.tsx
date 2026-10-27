"use client";

import { useEffect, useState } from "react";
import { Activity, ShieldCheck, CheckCircle2, Clock, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

export default function UsageDashboardPage() {
  const [summaries, setSummaries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getProviderUsageSummary();
        setSummaries(data);
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
      <div className="border-b border-border pb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">
          AI Provider Usage & Quota Monitoring
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Real-time request volumes, error rates, account cooldown statuses, and spending controls.
        </p>
      </div>

      <div className="rounded-2xl bg-surface border border-border overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-20 text-center text-slate-500 text-sm">
            Loading usage telemetry...
          </div>
        ) : summaries.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-xs italic">
            No active provider accounts recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-raised/80 text-slate-400 font-semibold border-b border-border uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-3 px-4">Account Label</th>
                  <th className="py-3 px-4">Provider</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Requests Today</th>
                  <th className="py-3 px-4">Success Rate</th>
                  <th className="py-3 px-4">Cooldown State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {summaries.map((item) => (
                  <tr key={item.account_id} className="hover:bg-surface-raised/40 transition">
                    <td className="py-3.5 px-4 font-bold text-white">
                      {item.account_name}
                    </td>
                    <td className="py-3.5 px-4 text-slate-300">
                      {item.provider_name}
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold ${
                          item.status === "HEALTHY"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : item.status === "COOLDOWN"
                            ? "bg-amber-500/10 text-amber-400"
                            : "bg-red-500/10 text-red-400"
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-300 font-semibold">
                      {item.requests_today}
                    </td>
                    <td className="py-3.5 px-4 text-slate-300">
                      {item.success_rate}%
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">
                      {item.cooldown_until ? `Active cooldown until ${new Date(item.cooldown_until).toLocaleTimeString()}` : "Normal Operations"}
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
