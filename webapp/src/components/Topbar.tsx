"use client";
import Link from "next/link";

export default function Topbar() {
  return (
    <header className="sticky top-0 z-50 border-b" style={{ background: "rgba(6,13,31,0.92)", borderColor: "var(--border)", backdropFilter: "blur(12px)" }}>
      <div className="max-w-[1400px] mx-auto px-6 h-13 flex items-center justify-between h-12">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-7 h-7 rounded-lg bg-[#3b7cf4] flex items-center justify-center text-white font-black text-sm">F</div>
          <span className="font-bold text-base tracking-tight" style={{ color: "var(--text)" }}>FinAnalyzer</span>
        </Link>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full border" style={{ color: "#3b7cf4", borderColor: "#1e3a5f", background: "rgba(59,124,244,0.08)" }}>
          Capstone By R001, R055 & R057
        </span>
      </div>
    </header>
  );
}
