"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Topbar from "@/components/Topbar";

const COMPANIES = [
  { slug: "INFY",     name: "Infosys Limited",            sector: "IT Services",   intrinsic: "₹1,432", rating: "Adequate" },
  { slug: "TCS",      name: "Tata Consultancy Services",  sector: "IT Services",   intrinsic: "₹2,361", rating: "Strong" },
  { slug: "RELIANCE", name: "Reliance Industries",        sector: "Energy",        intrinsic: "₹8,777", rating: "Strong" },
  { slug: "MARUTI",   name: "Maruti Suzuki India",        sector: "Automobile",    intrinsic: "₹5,227", rating: "Adequate" },
];

const FEATURES = [
  { icon: "📊", title: "Live KPI Snapshot",    desc: "Revenue, profit, FCF with YoY growth in real time" },
  { icon: "📈", title: "Combined Forecasts",   desc: "Bear / Base / Bull on one chart with history" },
  { icon: "💰", title: "DCF Valuation",        desc: "Dynamic WACC + 3D Monte Carlo + sensitivity surface" },
  { icon: "🔁", title: "DuPont Analysis",      desc: "5-factor ROE decomposition over 11 years" },
  { icon: "🤖", title: "AI Commentary",        desc: "Claude-powered investment thesis & red flags" },
  { icon: "📁", title: "Download Reports",     desc: "Full Excel workbook with all 9 analysis sheets" },
];

const ratingColor = (r: string) =>
  r === "Strong" ? "#00d68f" : r === "Adequate" ? "#ffb020" : "#ff3d57";

export default function Home() {
  const router = useRouter();
  const [search, setSearch] = useState("");

  const go = (slug: string) => router.push(`/${slug.trim().toUpperCase()}`);

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <Topbar />

      {/* ── Hero ── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{ background: "radial-gradient(ellipse 80% 50% at 50% -10%, rgba(59,124,244,0.12), transparent)" }} />
        <div className="max-w-[1400px] mx-auto px-6 py-20 text-center relative">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold mb-6 border" style={{ background: "rgba(59,124,244,0.08)", borderColor: "#1e3a5f", color: "#3b7cf4" }}>
            ✦ AI · Finance · Technology
          </div>
          <h1 className="text-5xl sm:text-6xl font-black tracking-tight mb-4 leading-tight">
            <span style={{ color: "var(--text)" }}>NSE / BSE</span>
            <br />
            <span className="gradient-text">Financial Intelligence</span>
          </h1>
          <p className="text-lg max-w-2xl mx-auto mb-10" style={{ color: "var(--text-2)" }}>
            End-to-end financial analysis — 11 years of history, 5-year forecasts, DCF valuation,
            3D Monte Carlo simulation, and AI-generated investment commentary.
          </p>

          {/* Search */}
          <form onSubmit={(e) => { e.preventDefault(); go(search); }} className="flex gap-2 max-w-md mx-auto mb-4">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Enter NSE/BSE ticker  (e.g. HDFCBANK)"
              className="flex-1 rounded-lg px-4 py-3 text-sm outline-none focus:border-[#3b7cf4] transition-colors"
              style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }}
            />
            <button type="submit" className="px-5 py-3 rounded-lg text-sm font-semibold transition-all hover:opacity-90 active:scale-95" style={{ background: "#3b7cf4", color: "#fff" }}>
              Analyse →
            </button>
          </form>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Analysed companies below · Any NSE/BSE slug supported after pipeline run
          </p>
        </div>
      </section>

      {/* ── Company Cards ── */}
      <section className="max-w-[1400px] mx-auto px-6 pb-16">
        <p className="section-title mb-6">Analysed Companies</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
          {COMPANIES.map((c) => (
            <button key={c.slug} onClick={() => go(c.slug)}
              className="text-left rounded-xl p-5 border transition-all hover:-translate-y-1 hover:border-[#2a4a7f] group"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
              <div className="flex items-start justify-between mb-3">
                <span className="text-2xl font-black" style={{ color: "#3b7cf4" }}>{c.slug}</span>
                <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ background: "rgba(59,124,244,0.1)", color: "#3b7cf4", border: "1px solid #1e3a5f" }}>
                  {c.sector}
                </span>
              </div>
              <p className="text-sm mb-4" style={{ color: "var(--text-2)" }}>{c.name}</p>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>DCF Intrinsic</p>
                  <p className="text-lg font-black" style={{ color: "#3b7cf4" }}>{c.intrinsic}</p>
                </div>
                <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{ color: ratingColor(c.rating), background: `${ratingColor(c.rating)}18`, border: `1px solid ${ratingColor(c.rating)}33` }}>
                  {c.rating}
                </span>
              </div>
              <p className="text-xs mt-3 group-hover:text-[#3b7cf4] transition-colors" style={{ color: "var(--text-muted)" }}>
                Open dashboard →
              </p>
            </button>
          ))}
        </div>

        {/* ── Features ── */}
        <p className="section-title mb-6">What&apos;s Inside</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-xl p-4 border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
              <div className="text-2xl mb-2">{f.icon}</div>
              <p className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>{f.title}</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
