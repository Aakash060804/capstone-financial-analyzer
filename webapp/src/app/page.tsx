"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const AVAILABLE = [
  { slug: "INFY",     name: "Infosys Limited",            sector: "IT",         color: "blue" },
  { slug: "TCS",      name: "Tata Consultancy Services",  sector: "IT",         color: "blue" },
  { slug: "RELIANCE", name: "Reliance Industries",        sector: "Energy",     color: "amber" },
  { slug: "MARUTI",   name: "Maruti Suzuki India",        sector: "Automobile", color: "green" },
];

const sectorColor: Record<string, string> = {
  IT:         "bg-blue-900/40 text-blue-300 border-blue-800",
  Energy:     "bg-amber-900/40 text-amber-300 border-amber-800",
  Automobile: "bg-emerald-900/40 text-emerald-300 border-emerald-800",
};

export default function Home() {
  const router = useRouter();
  const [search, setSearch] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const slug = search.trim().toUpperCase();
    if (slug) router.push(`/${slug}/`);
  };

  return (
    <div className="max-w-4xl mx-auto">

      {/* Hero */}
      <div className="text-center py-12">
        <p className="text-xs text-blue-400 uppercase tracking-widest font-semibold mb-3">
          Financial Analysis · Valuation · AI Insights
        </p>
        <h1 className="text-4xl sm:text-5xl font-extrabold mb-4">
          NSE / BSE Company
          <span className="text-blue-400"> Dashboard</span>
        </h1>
        <p className="text-gray-400 text-lg max-w-xl mx-auto mb-8">
          Explore 9 sheets of financial data — ratios, DuPont, DCF valuation,
          5-year forecasts, and AI-powered commentary.
        </p>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-2 max-w-md mx-auto">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Enter NSE/BSE ticker (e.g. HDFCBANK)"
            className="flex-1 bg-[#161d2e] border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-500 text-white font-semibold px-5 py-2.5 rounded-lg text-sm transition-colors"
          >
            Analyse →
          </button>
        </form>
      </div>

      {/* Available companies */}
      <div>
        <h2 className="text-sm text-gray-500 uppercase tracking-wider font-semibold mb-4">
          Available Reports
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {AVAILABLE.map((c) => (
            <button
              key={c.slug}
              onClick={() => router.push(`/${c.slug}/`)}
              className="bg-[#161d2e] border border-gray-800 hover:border-blue-600 rounded-xl p-5 text-left transition-all hover:-translate-y-0.5 group"
            >
              <div className="flex items-start justify-between mb-2">
                <span className="text-2xl font-extrabold text-blue-400 group-hover:text-blue-300">
                  {c.slug}
                </span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${sectorColor[c.sector]}`}>
                  {c.sector}
                </span>
              </div>
              <p className="text-gray-400 text-sm">{c.name}</p>
              <p className="text-xs text-gray-600 mt-2 group-hover:text-blue-500 transition-colors">
                View dashboard →
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Features */}
      <div className="mt-12 grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          ["📊", "Financial Statements", "Income, Balance Sheet & Cash Flow"],
          ["📈", "25+ Ratios", "Profitability, Liquidity, Solvency & more"],
          ["🔁", "DuPont Analysis", "5-factor ROE decomposition"],
          ["🚀", "5-Year Forecast", "Bull / Base / Bear scenarios"],
          ["💰", "DCF Valuation", "Dynamic WACC + Monte Carlo"],
          ["🤖", "AI Commentary", "Claude-powered insights & red flags"],
        ].map(([icon, title, desc]) => (
          <div key={title} className="bg-[#161d2e] border border-gray-800 rounded-xl p-4">
            <div className="text-2xl mb-2">{icon}</div>
            <p className="text-sm font-semibold text-white">{title}</p>
            <p className="text-xs text-gray-500 mt-1">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
