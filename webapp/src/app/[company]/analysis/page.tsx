"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FinancialData } from "@/types/financial";
import { buildHealthScore, getSeries, getLastValue, fmtNum } from "@/lib/dataUtils";
import SectionCard from "@/components/SectionCard";
import SparkLine from "@/components/SparkLine";
import FinTable from "@/components/FinTable";

// ── Health Score Ring ──────────────────────────────────────────────────────────
function ScoreRing({ score, size = 120 }: { score: number; size?: number }) {
  const r = (size / 2) - 10;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = score >= 70 ? "#00d68f" : score >= 45 ? "#ffb020" : "#ff3d57";
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1a2d4f" strokeWidth={10} />
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={color} strokeWidth={10}
        strokeDasharray={`${fill} ${circ - fill}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: "stroke-dasharray 0.8s ease" }}
      />
      <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle" fill={color} fontSize={size * 0.22} fontWeight="900">{score}</text>
      <text x="50%" y="67%" dominantBaseline="middle" textAnchor="middle" fill="#4a6080" fontSize={size * 0.1}>/ 100</text>
    </svg>
  );
}

// ── Score Bar ─────────────────────────────────────────────────────────────────
function ScoreBar({ label, score, weight }: { label: string; score: number; weight: string }) {
  const color = score >= 70 ? "bg-fin-green" : score >= 45 ? "bg-fin-amber" : "bg-fin-red";
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-txt2">{label}</span>
        <span className="text-muted">{weight} · <span className="text-txt font-semibold num">{score}</span></span>
      </div>
      <div className="h-1.5 rounded-full bg-surface2 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-700`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

// ── Ratio Card with Sparkline ─────────────────────────────────────────────────
function RatioCard({ label, value, unit, table, metric, signal }: {
  label: string; value: string; unit: string;
  table: import("@/types/financial").DataTable; metric: string;
  signal?: "pos" | "neg" | "neu";
}) {
  const cls = signal === "pos" ? "text-fin-green" : signal === "neg" ? "text-fin-red" : "text-txt";
  return (
    <div className="card-sm">
      <p className="text-xs text-muted uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-lg font-black num ${cls}`}>{value}<span className="text-xs font-normal text-muted ml-1">{unit}</span></p>
      <div className="mt-2">
        <SparkLine table={table} metric={metric} />
      </div>
    </div>
  );
}

const RATIO_CATEGORIES = [
  {
    key: "Profitability",
    title: "Profitability",
    metrics: [
      { metric: "Net Profit Margin (%)", label: "Net Profit Margin", unit: "%", goodAbove: 10 },
      { metric: "Return on Equity % (ROE)", label: "ROE", unit: "%", goodAbove: 15 },
      { metric: "Return on Capital Employed % (ROCE)", label: "ROCE", unit: "%", goodAbove: 15 },
      { metric: "Gross Profit Margin (%)", label: "Gross Margin", unit: "%", goodAbove: 30 },
    ],
  },
  {
    key: "Liquidity",
    title: "Liquidity",
    metrics: [
      { metric: "Current Ratio (x)", label: "Current Ratio", unit: "x", goodAbove: 1.5 },
      { metric: "Quick Ratio (x)", label: "Quick Ratio", unit: "x", goodAbove: 1 },
      { metric: "Cash Ratio (x)", label: "Cash Ratio", unit: "x", goodAbove: 0.5 },
    ],
  },
  {
    key: "Solvency",
    title: "Solvency / Leverage",
    metrics: [
      { metric: "Debt-to-Equity (x)", label: "Debt / Equity", unit: "x", goodBelow: 1 },
      { metric: "Interest Coverage (x)", label: "Interest Coverage", unit: "x", goodAbove: 5 },
      { metric: "Debt-to-Assets (x)", label: "Debt / Assets", unit: "x", goodBelow: 0.5 },
    ],
  },
  {
    key: "Efficiency",
    title: "Efficiency",
    metrics: [
      { metric: "Asset Turnover (x)", label: "Asset Turnover", unit: "x", goodAbove: 1 },
      { metric: "Inventory Turnover (x)", label: "Inventory Turnover", unit: "x", goodAbove: 5 },
      { metric: "Receivables Turnover (x)", label: "Receivables Turnover", unit: "x", goodAbove: 8 },
    ],
  },
  {
    key: "Growth",
    title: "Growth",
    metrics: [
      { metric: "Revenue Growth (%)", label: "Revenue Growth", unit: "%", goodAbove: 10 },
      { metric: "Net Income Growth (%)", label: "Net Income Growth", unit: "%", goodAbove: 10 },
      { metric: "EPS Growth (%)", label: "EPS Growth", unit: "%", goodAbove: 10 },
    ],
  },
  {
    key: "Cash Flow",
    title: "Cash Flow",
    metrics: [
      { metric: "FCF Margin (%)", label: "FCF Margin", unit: "%", goodAbove: 10 },
      { metric: "Operating CF Margin (%)", label: "CFO Margin", unit: "%", goodAbove: 15 },
      { metric: "FCF Yield (%)", label: "FCF Yield", unit: "%", goodAbove: 5 },
    ],
  },
];

export default function AnalysisPage() {
  const { company } = useParams() as { company: string };
  const [data, setData] = useState<FinancialData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/data/${company?.toUpperCase()}_financial_data.json`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [company]);

  if (loading) return <div className="flex items-center justify-center h-64 text-muted animate-pulse">Loading analysis…</div>;
  if (!data) return <div className="text-fin-red text-sm">No data. Run the pipeline first.</div>;

  const score = buildHealthScore(data);
  const scoreColor = score.total >= 70 ? "text-fin-green" : score.total >= 45 ? "text-fin-amber" : "text-fin-red";
  const scoreLabel = score.total >= 70 ? "Healthy" : score.total >= 45 ? "Moderate" : "Weak";

  const audit = data.audit;
  const peers = audit?.industry_classification?.peers ?? [];
  const peerMedians = audit?.industry_classification?.peer_medians ?? {};
  const redFlags = data.ai_commentary?.red_flags;
  const aiCategories = data.ai_commentary?.categories ?? [];
  const dupont = data.dupont;

  // Get last value from ratio table
  const getRV = (cat: string, metric: string): number | null => {
    const tbl = (data.ratios as Record<string, import("@/types/financial").DataTable>)[cat];
    if (!tbl) return null;
    const row = tbl.rows.find((r) => String(r.metric) === metric);
    if (!row) return null;
    const years = tbl.headers.filter((h) => h !== "metric");
    for (let i = years.length - 1; i >= 0; i--) {
      const v = row[years[i]];
      if (typeof v === "number" && !isNaN(v)) return v;
    }
    return null;
  };

  return (
    <div className="space-y-8">

      {/* ── Financial Health Score ── */}
      <SectionCard title="Financial Health Score" subtitle="Composite score across 5 dimensions — higher is better">
        <div className="flex flex-col sm:flex-row items-center gap-8">
          <div className="flex flex-col items-center gap-2">
            <ScoreRing score={score.total} size={140} />
            <span className={`text-sm font-black uppercase tracking-wider ${scoreColor}`}>{scoreLabel}</span>
          </div>
          <div className="flex-1 w-full space-y-3">
            <ScoreBar label="Profitability" score={score.profitability} weight="30%" />
            <ScoreBar label="Solvency / Leverage" score={score.solvency} weight="20%" />
            <ScoreBar label="Growth" score={score.growth} weight="20%" />
            <ScoreBar label="Liquidity" score={score.liquidity} weight="15%" />
            <ScoreBar label="Cash Flow Quality" score={score.cashFlow} weight="15%" />
          </div>
        </div>
      </SectionCard>

      {/* ── Ratio Cards by Category ── */}
      {RATIO_CATEGORIES.map((cat) => {
        const tbl = (data.ratios as Record<string, import("@/types/financial").DataTable>)[cat.key];
        if (!tbl) return null;
        const cards = cat.metrics.map((m) => {
          const val = getRV(cat.key, m.metric);
          const fmtVal = val !== null ? fmtNum(val, "", 2) : "—";
          let signal: "pos" | "neg" | "neu" = "neu";
          if (val !== null) {
            if ("goodAbove" in m && m.goodAbove !== undefined) {
              signal = val >= m.goodAbove ? "pos" : val >= m.goodAbove * 0.5 ? "neu" : "neg";
            } else if ("goodBelow" in m && m.goodBelow !== undefined) {
              signal = val <= m.goodBelow ? "pos" : val <= m.goodBelow * 2 ? "neu" : "neg";
            }
          }
          return { ...m, fmtVal, signal, tbl };
        }).filter((c) => {
          const row = tbl.rows.find((r) => String(r.metric) === c.metric);
          return !!row;
        });
        if (cards.length === 0) return null;
        return (
          <SectionCard key={cat.key} title={cat.title} subtitle="Last value highlighted · sparkline shows 10-year trend">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {cards.map((c) => (
                <RatioCard
                  key={c.metric}
                  label={c.label}
                  value={c.fmtVal}
                  unit={c.unit}
                  table={c.tbl}
                  metric={c.metric}
                  signal={c.signal}
                />
              ))}
            </div>
          </SectionCard>
        );
      })}

      {/* ── DuPont Analysis ── */}
      {dupont?.rows?.length > 0 && (
        <SectionCard title="DuPont Decomposition" subtitle="ROE = Net Margin × Asset Turnover × Equity Multiplier">
          <FinTable table={dupont} highlightRows={["ROE (%)", "Net Profit Margin (%)", "Asset Turnover (x)", "Equity Multiplier (x)"]} />
        </SectionCard>
      )}

      {/* ── Common Size Statements ── */}
      {data.common_size?.income_statement?.rows?.length > 0 && (
        <SectionCard title="Common Size Income Statement" subtitle="Each line as % of Revenue — shows structural margin trends">
          <FinTable table={data.common_size.income_statement} lastNYears={7} />
        </SectionCard>
      )}

      {/* ── Working Capital & Debt Schedule ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {data.schedules?.working_capital?.rows?.length > 0 && (
          <SectionCard title="Working Capital Schedule" subtitle="₹ Crores">
            <FinTable table={data.schedules.working_capital} lastNYears={5} compact />
          </SectionCard>
        )}
        {data.schedules?.debt?.rows?.length > 0 && (
          <SectionCard title="Debt Schedule" subtitle="₹ Crores">
            <FinTable table={data.schedules.debt} lastNYears={5} compact />
          </SectionCard>
        )}
      </div>

      {/* ── Peer Benchmarking ── */}
      {peers.length > 0 && (
        <SectionCard title="Peer Benchmarking" subtitle={`Industry: ${audit.industry_classification.sector} · Sector median vs. ${company?.toUpperCase()}`}>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="fin-table">
              <thead>
                <tr>
                  <th className="text-left">Metric</th>
                  <th className="text-right text-accent">{company?.toUpperCase()}</th>
                  <th className="text-right text-muted">Sector Median</th>
                  <th className="text-right">vs. Peers</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(peerMedians).map(([metric, median]) => {
                  const parts = metric.split("_");
                  const cat = parts[0];
                  const met = parts.slice(1).join("_");
                  const ourVal = getRV(cat, met);
                  const diff = ourVal !== null ? ourVal - median : null;
                  return (
                    <tr key={metric}>
                      <td className="text-txt2">{metric.replace(/_/g, " ")}</td>
                      <td className="text-right font-semibold num text-accent">{ourVal !== null ? fmtNum(ourVal, "", 2) : "—"}</td>
                      <td className="text-right num text-muted">{fmtNum(median, "", 2)}</td>
                      <td className="text-right">
                        {diff !== null ? (
                          <span className={`text-xs font-semibold num ${diff > 0 ? "text-fin-green" : "text-fin-red"}`}>
                            {diff > 0 ? "+" : ""}{fmtNum(diff, "", 2)}
                          </span>
                        ) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {peers.length > 0 && (
            <p className="text-xs text-muted mt-2">Peer universe: {peers.join(" · ")}</p>
          )}
        </SectionCard>
      )}

      {/* ── Red Flags ── */}
      {redFlags?.flags?.length > 0 && (
        <SectionCard title="Risk & Red Flags" subtitle={`Overall Risk: ${redFlags.overall_risk} · ${redFlags.total_flags} flag(s) detected`}>
          <div className="mb-4 p-3 rounded-lg bg-fin-red/5 border border-fin-red/20">
            <p className="text-xs text-txt2 leading-relaxed">{redFlags.risk_summary}</p>
          </div>
          <div className="space-y-2">
            {redFlags.flags.map((flag, i) => {
              const sev = flag.severity === "high" ? "border-fin-red/40 bg-fin-red/5" : flag.severity === "medium" ? "border-fin-amber/40 bg-fin-amber/5" : "border-border bg-surface2";
              const sevTxt = flag.severity === "high" ? "text-fin-red" : flag.severity === "medium" ? "text-fin-amber" : "text-muted";
              return (
                <div key={i} className={`rounded-lg border p-3 ${sev}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-black uppercase tracking-wider ${sevTxt}`}>{flag.severity}</span>
                        <span className="text-xs text-muted">·</span>
                        <span className="text-xs text-txt2 font-semibold">{flag.metric}</span>
                        {flag.value && <span className="text-xs text-muted">= {flag.value}</span>}
                      </div>
                      <p className="text-xs text-txt2 leading-relaxed">{flag.explanation}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>
      )}

      {/* ── AI Category Commentary ── */}
      {aiCategories.length > 0 && (
        <SectionCard title="AI Commentary by Category" subtitle="LLM-generated analysis across financial dimensions">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {aiCategories.map((cat) => {
              const trendColor = cat.trend === "improving" ? "text-fin-green border-fin-green/30 bg-fin-green/5"
                : cat.trend === "deteriorating" ? "text-fin-red border-fin-red/30 bg-fin-red/5"
                : "text-fin-amber border-fin-amber/30 bg-fin-amber/5";
              return (
                <div key={cat.category} className="rounded-xl border border-border p-4 bg-surface2">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <p className="text-xs font-black uppercase tracking-wider text-accent">{cat.category}</p>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${trendColor}`}>
                      {cat.trend}
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-txt mb-1">{cat.headline}</p>
                  <p className="text-xs text-txt2 leading-relaxed">{cat.commentary}</p>
                </div>
              );
            })}
          </div>
        </SectionCard>
      )}

      {/* ── Balance Sheet ── */}
      <SectionCard title="Balance Sheet" subtitle="Full history · ₹ Crores">
        <FinTable
          table={data.statements.balance_sheet}
          highlightRows={["Total Assets", "Total Equity", "Total Liabilities"]}
          lastNYears={7}
        />
      </SectionCard>

      {/* ── Common Size Balance Sheet ── */}
      {data.common_size?.balance_sheet?.rows?.length > 0 && (
        <SectionCard title="Common Size Balance Sheet" subtitle="Each line as % of Total Assets">
          <FinTable table={data.common_size.balance_sheet} lastNYears={7} />
        </SectionCard>
      )}
    </div>
  );
}
