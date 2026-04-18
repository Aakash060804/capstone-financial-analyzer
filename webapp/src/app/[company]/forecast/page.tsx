"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FinancialData } from "@/types/financial";
import { buildScenarioInsights, getSeries, getLastValue, cagr, fmtCr, getYears } from "@/lib/dataUtils";
import SectionCard from "@/components/SectionCard";
import CombinedScenarioChart from "@/components/CombinedScenarioChart";
import FinTable from "@/components/FinTable";

export default function ForecastPage() {
  const { company } = useParams() as { company: string };
  const [data, setData] = useState<FinancialData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/data/${company?.toUpperCase()}_financial_data.json`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [company]);

  if (loading) return <div className="flex items-center justify-center h-64 text-muted animate-pulse">Loading forecasts…</div>;
  if (!data) return <div className="text-fin-red text-sm">No data. Run the pipeline first.</div>;

  const sc = data.forecasts.scenarios;
  const hasScenarios = sc?.base?.rows?.length > 0;
  const comparisons = buildScenarioInsights(data);
  const forecastYears = sc?.base?.headers?.filter((h) => h !== "metric") ?? [];
  const lastFY = forecastYears[forecastYears.length - 1];

  // Per-scenario CAGR
  const lastHistRev = getLastValue(data.statements.income_statement, "Sales");
  const scenarioCagr = (s: typeof sc.base) => {
    const last = s?.rows?.find((r) => String(r.metric) === "Revenue")?.[lastFY];
    return cagr(lastHistRev, typeof last === "number" ? last : null, forecastYears.length);
  };

  const scenarios = [
    { key: "base", label: "Base Case",  color: "text-accent",    bg: "bg-accent/10    border-accent/20",    cagrVal: scenarioCagr(sc.base) },
    { key: "bull", label: "Bull Case",  color: "text-fin-green", bg: "bg-fin-green/10 border-fin-green/20", cagrVal: scenarioCagr(sc.bull) },
    { key: "bear", label: "Bear Case",  color: "text-fin-red",   bg: "bg-fin-red/10   border-fin-red/20",   cagrVal: scenarioCagr(sc.bear) },
  ] as const;

  if (!hasScenarios) return (
    <div className="text-muted text-sm">Forecasts not generated. Run without <code>--no-forecast</code>.</div>
  );

  return (
    <div className="space-y-8">

      {/* ── Scenario Summary Cards ── */}
      <div>
        <p className="section-title">5-Year Scenario Overview  ·  {data.meta?.company_slug}</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          {scenarios.map((s) => {
            const tbl = (sc as Record<string, typeof sc.base>)[s.key];
            const revLast = tbl?.rows?.find((r) => String(r.metric) === "Revenue")?.[lastFY];
            const niLast  = tbl?.rows?.find((r) => String(r.metric) === "Net Income")?.[lastFY];
            const fcfLast = tbl?.rows?.find((r) => String(r.metric) === "Free Cash Flow")?.[lastFY];
            return (
              <div key={s.key} className={`card-sm border ${s.bg}`}>
                <p className={`text-xs font-black uppercase tracking-widest mb-3 ${s.color}`}>{s.label}</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted">Revenue by {lastFY}</span>
                    <span className={`font-bold num ${s.color}`}>{fmtCr(typeof revLast === "number" ? revLast : null)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Net Income</span>
                    <span className="font-semibold text-txt2 num">{fmtCr(typeof niLast === "number" ? niLast : null)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Free Cash Flow</span>
                    <span className="font-semibold text-txt2 num">{fmtCr(typeof fcfLast === "number" ? fcfLast : null)}</span>
                  </div>
                  <div className="flex justify-between border-t border-border pt-2 mt-2">
                    <span className="text-muted">Revenue CAGR</span>
                    <span className={`font-black num ${s.color}`}>
                      {s.cagrVal !== null ? `${s.cagrVal.toFixed(1)}%` : "—"}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Combined Revenue Chart ── */}
      <SectionCard title="Revenue Forecast" subtitle="Historical + Bear / Base / Bull · ₹ Crores">
        <CombinedScenarioChart
          data={data}
          historicMetric="Sales"
          forecastMetric="Revenue"
          title="Revenue: 11 Years History + 5 Year Forecast"
        />
      </SectionCard>

      {/* ── Combined Net Income Chart ── */}
      <SectionCard title="Net Income Forecast" subtitle="Historical + 3 Scenarios · ₹ Crores">
        <CombinedScenarioChart
          data={data}
          historicMetric="Net Profit"
          forecastMetric="Net Income"
          title="Net Income: History + Forecast"
        />
      </SectionCard>

      {/* ── Combined FCF Chart ── */}
      <SectionCard title="Free Cash Flow Forecast" subtitle="Historical + 3 Scenarios · ₹ Crores">
        <CombinedScenarioChart
          data={data}
          historicMetric="Free Cash Flow"
          forecastMetric="Free Cash Flow"
          title="Free Cash Flow: History + Forecast"
        />
      </SectionCard>

      {/* ── Scenario Comparison Table ── */}
      <SectionCard title="Scenario Comparison" subtitle="Side-by-side Bear · Base · Bull">
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="fin-table">
            <thead>
              <tr>
                <th className="text-left">Metric</th>
                {scenarios.map((s) => (
                  <th key={s.key} className={`text-right ${s.color}`}>{s.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparisons.map((row, i) => (
                <tr key={i}>
                  <td>{row.label}</td>
                  <td className="text-right text-fin-red font-semibold num">{row.bear}</td>
                  <td className="text-right text-accent font-semibold num">{row.base}</td>
                  <td className="text-right text-fin-green font-semibold num">{row.bull}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      {/* ── Derived Forecast Insights ── */}
      <SectionCard title="Forecast Insights" subtitle="Derived from scenario projections">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {scenarios.map((s) => {
            const tbl = (sc as Record<string, typeof sc.base>)[s.key];
            const revFirst = tbl?.rows?.find((r) => String(r.metric) === "Revenue")?.[forecastYears[0]];
            const revLast  = tbl?.rows?.find((r) => String(r.metric) === "Revenue")?.[lastFY];
            const opmLast  = tbl?.rows?.find((r) => String(r.metric) === "OPM %")?.[lastFY];
            const fcfMargin = tbl?.rows?.find((r) => String(r.metric) === "FCF Margin (%)")?.[lastFY];
            const roe       = tbl?.rows?.find((r) => String(r.metric) === "ROE (%) est.")?.[lastFY];
            return (
              <div key={s.key} className={`rounded-xl p-4 border ${s.bg}`}>
                <p className={`text-xs font-black uppercase tracking-widest mb-3 ${s.color}`}>{s.label}</p>
                <ul className="space-y-2 text-sm">
                  <li className="flex justify-between">
                    <span className="text-muted">OPM % ({lastFY})</span>
                    <span className="font-semibold text-txt2 num">{typeof opmLast === "number" ? `${opmLast.toFixed(1)}%` : "—"}</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-muted">FCF Margin ({lastFY})</span>
                    <span className="font-semibold text-txt2 num">{typeof fcfMargin === "number" ? `${fcfMargin.toFixed(1)}%` : "—"}</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-muted">ROE est. ({lastFY})</span>
                    <span className="font-semibold text-txt2 num">{typeof roe === "number" ? `${roe.toFixed(1)}%` : "—"}</span>
                  </li>
                  <li className="flex justify-between border-t border-border pt-2">
                    <span className="text-muted">Rev Growth CAGR</span>
                    <span className={`font-black num ${s.color}`}>{s.cagrVal !== null ? `${s.cagrVal.toFixed(1)}%` : "—"}</span>
                  </li>
                </ul>
              </div>
            );
          })}
        </div>
      </SectionCard>

      {/* ── Detailed Forecast Tables ── */}
      {scenarios.map((s) => (
        <SectionCard key={s.key} title={`${s.label} — Detailed Table`} subtitle={`All 18 metrics · ${forecastYears[0]} to ${lastFY}`}>
          <FinTable
            table={(sc as Record<string, typeof sc.base>)[s.key]}
            highlightRows={["Revenue", "Net Income", "Free Cash Flow", "OPM %"]}
          />
        </SectionCard>
      ))}
    </div>
  );
}
