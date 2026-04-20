"use client";
import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 bg-[#0b0f1a]/90 backdrop-blur border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="text-blue-400 font-bold text-lg tracking-tight hover:text-blue-300 transition-colors">
          FinAnalyzer
        </Link>
        <span className="text-xs bg-blue-900/40 text-blue-300 border border-blue-800 px-2.5 py-1 rounded-full font-semibold">
          Capstone By R001, R055 & R057
        </span>
      </div>
    </nav>
  );
}
