"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Film,
  PlusCircle,
  Clock,
  KeyRound,
  FolderOpen,
  Mic,
  Activity,
  Cpu,
  Settings,
  Sparkles,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { label: "Dashboard", href: "/", icon: Film },
    { label: "New Video", href: "/new", icon: PlusCircle, highlight: true },
    { label: "Render Queue", href: "/queue", icon: Clock },
    { label: "AI Providers", href: "/settings/providers", icon: KeyRound, badge: "Security" },
    { label: "Media Assets", href: "/assets", icon: FolderOpen },
    { label: "Voice Studio", href: "/voices", icon: Mic },
    { label: "Usage & Quotas", href: "/settings/usage", icon: Activity },
    { label: "Model Registry", href: "/settings/models", icon: Cpu },
  ];

  return (
    <aside className="w-64 bg-surface border-r border-border flex flex-col h-screen fixed left-0 top-0 z-30">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-border gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <span className="font-bold text-base text-white tracking-tight">
            AI Video Studio
          </span>
          <span className="block text-[10px] uppercase font-semibold tracking-wider text-accent-cyan">
            Local Pro Studio
          </span>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? "bg-primary text-white shadow-md shadow-primary/25"
                  : item.highlight
                  ? "bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 border border-blue-500/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-surface-raised"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-white" : ""}`} />
              <span className="flex-1">{item.label}</span>
              {item.badge && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-semibold">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* System Status Footprint */}
      <div className="p-4 border-t border-border">
        <div className="p-3 rounded-lg bg-surface-raised border border-border/80">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-medium text-slate-300">Local Engine</span>
            <span className="flex items-center gap-1.5 text-accent-emerald">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-emerald animate-pulse" />
              Ready
            </span>
          </div>
          <p className="text-[11px] text-slate-500 truncate">
            Apple Silicon • MPS Active
          </p>
        </div>
      </div>
    </aside>
  );
}
