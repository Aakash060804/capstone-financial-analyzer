"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FinancialData } from "@/types/financial";
import { buildSnapshotKPIs, buildDerivedInsights, getSeries } from "@/lib/dataUtils";
import KPICard from "@/components/KPICard";
import SectionCard from "@/components/SectionCard";
import FinTable from "@/components/FinTable";
import GrowthBadge from "@/components/GrowthBadge";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

export default function SnapshotPage() {
  const { company } = useParams() as { company: string };
  const slug = company?.toUpperCase() ?? "";

  const [data, setData] = useState<FinancialData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/data/${slug}_financial_data.json`)
      .then((r) => { if (!r.ok) throw new Error("not found"); return r.json(); })
      .then((d: FinancialData) => { setData(d); setLoading(false); })
      .catch(() => { setError("No data found. Run the pipeline first."); setLoading(false); });
  }, [slug]);

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-muted">
      <div className="text-center"><div className="text-4xl mb-3 animate-pulse">⏳</div><p>Loading {slug}…</p></div>
    </div>
  );

  if (error || !data) return (
    <div className="max-w-lg mx-auto mt-10 rounded-xl border border-fin-red/30 bg-fin-red/5 p-6 text-center">
      <p className="text-fin-red font-semibold mb-2">Data Not Found</p>
      <p className="text-txt2 text-sm mb-4">{error}</p>
      <pre className="text-left bg-surface2 rounded-lg p-3 text-xs text-txt2 overflow-x-auto">
{`cd financial_analyzer
python main.py --company ${slug}
cp outputs/${slug}_financial_data.json ../webapp/public/data/`}
      </pre>
    </div>
  );

  const kpis    = buildSnapshotKPIs(data);
  const insights = buildDerivedInsights(data);
  const inc      = data.statements.income_statement;
  const cf       = data.statements.cash_flow;

  // Revenue + Net Profit bar+line chart
  const revSeries = getSeries(inc, "Sales");
  const npSeries  = getSeries(inc, "Net Profit");
  const chartData = revSeries.map((p, i) => ({
    year: p.year.replace("Mar ", "'"),
    Revenue: p.value,
    "Net Profit": npSeries[i]?.value ?? null,
  }));

  // Cash flow chart
  const cfoSeries = getSeries(cf, "Cash from Operating Activity");
  const fcfSeries = getSeries(cf, "Free Cash Flow");
  const ncfSeries = getSeries(cf, "Net Cash Flow");
  const cfData = cfoSeries.map((p, i) => ({
    year: p.year.replace("Mar ", "'"),
    CFO: p.value,
    FCF: fcfSeries[i]?.value ?? null,
    "Net CF": ncfSeries[i]?.value ?? null,
  }));

  const signalClass = (s: string) =>
    s === "positive" ? "text-fin-green" : s === "negative" ? "text-fin-red" : "text-fin-amber";

  return (
    <div className="space-y-8">

      {/* ── KPI Grid ── */}
      <div>
        <p className="section-title">Key Performance Indicators</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {kpis.map((k) => <KPICard key={k.label} kpi={k} highlight={k.label === "Revenue" || k.label === "Net Profit"} />)}
        </div>
      </div>

      {/* ── Derived Insights ── */}
      <div>
        <p className="section-title">Derived Insights</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {insights.map((ins) => (
            <div key={ins.title} className="card-sm flex flex-col gap-2">
              <p className="text-xs font-semibold text-muted uppercase tracking-wider">{ins.title}</p>
              <p className={`text-2xl font-black num ${signalClass(ins.signal)}`}>{ins.value}</p>
              <p className="text-xs text-txt2 leading-relaxed">{ins.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Charts row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Revenue + Net Profit */}
        <SectionCard title="Revenue & Net Profit" subtitle="₹ Crores — 11-year history">
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a2d4f" vertical={false} />
              <XAxis dataKey="year" tick={{ fill: "#4a6080", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "#1a2d4f" }} />
              <YAxis yAxisId="left" tick={{ fill: "#4a6080", fontSize: 10 }} tickLine={false} axisLine={false}
                tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} width={55} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: "#4a6080", fontSize: 10 }} tickLine={false} axisLine={false}
                tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} width={55} />
              <Tooltip
                contentStyle={{ background: "#0c1529", border: "1px solid #1a2d4f", borderRadius: 8, fontSize: 12 }}
                formatter={(v: number) => [`₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`, ""]}
              />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 12, color: "#94a3b8" }} />
              <Bar yAxisId="left" dataKey="Revenue" fill="#3b7cf4" fillOpacity={0.7} radius={[3, 3, 0, 0]} />
              <Line yAxisId="right" type="monotone" dataKey="Net Profit" stroke="#00d68f" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        </SectionCard>

        {/* Cash Flow trifecta */}
        <SectionCard title="Cash Flow Trifecta" subtitle="CFO · FCF · Net Cash Flow (₹ Cr)">
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={cfData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a2d4f" vertical={false} />
              <XAxis dataKey="year" tick={{ fill: "#4a6080", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "#1a2d4f" }} />
              <YAxis tick={{ fill: "#4a6080", fontSize: 10 }} tickLine={false} axisLine={false}
                tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} width={55} />
              <Tooltip
                contentStyle={{ background: "#0c1529", border: "1px solid #1a2d4f", borderRadius: 8, fontSize: 12 }}
                formatter={(v: number) => [`₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`, ""]}
              />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 12, color: "#94a3b8" }} />
              <Line type="monotone" dataKey="CFO"    stroke="#3b7cf4" strokeWidth={2} dot={false} connectNulls />
              <Line type="monotone" dataKey="FCF"    stroke="#00d68f" strokeWidth={2} dot={false} connectNulls />
              <Line type="monotone" dataKey="Net CF" stroke="#ffb020" strokeWidth={2} dot={false} connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        </SectionCard>
      </div>

      {/* ── AI Thesis ── */}
      {data.ai_commentary?.thesis?.executive_summary && (
        <SectionCard title="AI Investment Thesis">
          <div className="flex flex-col sm:flex-row gap-6">
            <div className="flex-1">
              <p className="text-sm text-txt2 leading-relaxed">{data.ai_commentary.thesis.executive_summary}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                <div>
                  <p className="text-xs font-semibold text-fin-green uppercase tracking-wider mb-2">Key Strengths</p>
                  {data.ai_commentary.thesis.key_strengths?.map((s, i) => (
                    <p key={i} className="text-xs text-txt2 flex gap-2 mb-1"><span className="text-fin-green">✓</span>{s}</p>
                  ))}
                </div>
                <div>
                  <p className="text-xs font-semibold text-fin-red uppercase tracking-wider mb-2">Key Concerns</p>
                  {data.ai_commentary.thesis.key_concerns?.map((c, i) => (
                    <p key={i} className="text-xs text-txt2 flex gap-2 mb-1"><span className="text-fin-red">✗</span>{c}</p>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex-shrink-0 flex flex-col gap-3">
              <div className="card-sm text-center min-w-[120px]">
                <p className="text-xs text-muted mb-1">Overall Rating</p>
                <p className={`text-xl font-black ${signalClass(data.ai_commentary.thesis.overall_rating === "Strong" ? "positive" : data.ai_commentary.thesis.overall_rating === "Adequate" ? "neutral" : "negative")}`}>
                  {data.ai_commentary.thesis.overall_rating}
                </p>
              </div>
              <div className="card-sm text-center">
                <p className="text-xs text-muted mb-1">Risk Level</p>
                <p className="text-lg font-bold text-fin-green">{data.ai_commentary.red_flags?.overall_risk ?? "—"}</p>
              </div>
            </div>
          </div>
        </SectionCard>
      )}

      {/* ── Income Statement (last 5 years) ── */}
      <SectionCard title="Income Statement" subtitle="Last 5 years · ₹ Crores">
        <FinTable
          table={data.statements.income_statement}
          highlightRows={["Sales", "Operating Profit", "Net Profit"]}
          lastNYears={5}
        />
      </SectionCard>

      {/* ── Cash Flow (last 5 years) ── */}
      <SectionCard title="Cash Flow Statement" subtitle="Last 5 years · ₹ Crores">
        <FinTable
          table={data.statements.cash_flow}
          highlightRows={["Cash from Operating Activity", "Free Cash Flow", "Net Cash Flow"]}
          lastNYears={5}
          compact
        />
      </SectionCard>
    </div>
  );
}
