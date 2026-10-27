"use client";

import Link from "next/link";
import { PlusCircle, ShieldCheck, Terminal, HardDrive } from "lucide-react";

export function Navbar() {
  return (
    <header className="h-16 bg-surface/80 backdrop-blur-md border-b border-border fixed top-0 right-0 left-64 z-20 px-8 flex items-center justify-between">
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-raised border border-border text-slate-300">
          <ShieldCheck className="w-3.5 h-3.5 text-accent-emerald" />
          <span>Encrypted Credentials at Rest</span>
        </div>
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-raised border border-border text-slate-400">
          <HardDrive className="w-3.5 h-3.5 text-accent-cyan" />
          <span>Local Storage Mode</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Link
          href="/new"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold shadow-md shadow-primary/20 transition"
        >
          <PlusCircle className="w-4 h-4" />
          <span>New Project</span>
        </Link>
      </div>
    </header>
  );
}
