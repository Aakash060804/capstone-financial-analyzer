"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { FinancialData } from "@/types/financial";
import Tabs from "@/components/ui/Tabs";
import StatCard from "@/components/ui/StatCard";
import Badge from "@/components/ui/Badge";
import FinancialTable from "@/components/FinancialTable";
import TrendChart from "@/components/TrendChart";
import SensitivityHeatmap from "@/components/SensitivityHeatmap";
import MonteCarloChart from "@/components/MonteCarloChart";
import AIInsights from "@/components/AIInsights";

// ─── helpers ─────────────────────────────────────────────────────────────────
function fmt(v: number | null | undefined, prefix = "", suffix = "", decimals = 1) {
  if (v === null || v === undefined) return "N/A";
  return `${prefix}${v.toLocaleString("en-IN", { maximumFractionDigits: decimals })}${suffix}`;
}

function latestValue(ratios: FinancialData["ratios"], category: string, metric: string): number | null {
  const table = ratios?.[category];
  if (!table?.rows?.length) return null;
  const row = table.rows.find((r) => String(r.metric) === metric);
  if (!row) return null;
  const years = table.headers.filter((h) => h !== "metric");
  for (let i = years.length - 1; i >= 0; i--) {
    const v = row[years[i]];
    if (typeof v === "number" && !isNaN(v)) return v;
  }
  return null;
}

const TABS = [
  { id: "overview",    label: "Overview" },
  { id: "statements",  label: "Statements" },
  { id: "ratios",      label: "Ratios" },
  { id: "dupont",      label: "DuPont & Common Size" },
  { id: "schedules",   label: "Schedules" },
  { id: "forecasts",   label: "Forecasts" },
  { id: "valuation",   label: "DCF Valuation" },
  { id: "ai",          label: "AI Insights" },
  { id: "audit",       label: "Audit" },
];

// ─── main component ───────────────────────────────────────────────────────────
export default function CompanyDashboard() {
  const params = useParams();
  const company = (params?.company as string)?.toUpperCase() ?? "";

  const [data, setData] = useState<FinancialData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    if (!company) return;
    setLoading(true);
    setError(null);
    fetch(`/data/${company}_financial_data.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`No data found for "${company}". Run the pipeline first.`);
        return r.json();
      })
      .then((d: FinancialData) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [company]);

  if (loading) return (
    <div className="flex items-center justify-center h-60 text-gray-400">
      <div className="text-center">
        <div className="text-4xl mb-3 animate-pulse">⏳</div>
        <p>Loading {company}…</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="bg-red-900/20 border border-red-800 rounded-xl p-6 max-w-xl mx-auto text-center mt-10">
      <p className="text-red-400 text-lg font-semibold mb-2">Data Not Found</p>
      <p className="text-gray-400 text-sm mb-4">{error}</p>
      <div className="bg-gray-900 rounded-lg p-3 text-left text-sm font-mono text-gray-300">
        <p className="text-gray-500 mb-1"># Generate JSON output:</p>
        <p>cd financial_analyzer</p>
        <p>python main.py --company {company}</p>
        <p className="text-gray-500 mt-2 mb-1"># Copy to webapp:</p>
        <p>cp outputs/{company}_financial_data.json ../webapp/public/data/</p>
      </div>
    </div>
  );

  if (!data) return null;

  const { meta, statements, ratios, dupont, common_size, schedules, forecasts, ai_commentary, audit } = data;
  const dcf = forecasts?.dcf;
  const mc = dcf?.monte_carlo;

  // ── Overview stat cards ──────────────────────────────────────────────────
  const roe    = latestValue(ratios, "Profitability", "Return on Equity % (ROE)");
  const roce   = latestValue(ratios, "Profitability", "Return on Capital Employed % (ROCE)");
  const npm    = latestValue(ratios, "Profitability", "Net Profit Margin (%)");
  const cr     = latestValue(ratios, "Liquidity", "Current Ratio (x)");
  const de     = latestValue(ratios, "Solvency", "Debt-to-Equity (x)");
  const ic     = latestValue(ratios, "Solvency", "Interest Coverage (x)");
  const intrinsic = dcf?.valuation?.intrinsic_value_per_share;

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-3xl font-extrabold text-white">{meta.company_slug}</h1>
            {audit?.industry_classification?.sector && (
              <Badge label={audit.industry_classification.sector} variant="blue" />
            )}
            {ai_commentary?.thesis?.overall_rating && (
              <Badge
                label={ai_commentary.thesis.overall_rating}
                variant={ai_commentary.thesis.overall_rating === "Strong" ? "green" : ai_commentary.thesis.overall_rating === "Adequate" ? "amber" : "red"}
              />
            )}
          </div>
          <p className="text-gray-400 mt-1">{meta.company_name}</p>
          <p className="text-xs text-gray-600 mt-0.5">
            {meta.currency} · Face Value ₹{meta.face_value_inr} · {meta.source}
          </p>
        </div>
        {intrinsic && (
          <div className="bg-blue-900/20 border border-blue-800 rounded-xl px-5 py-3 text-right">
            <p className="text-xs text-blue-400 uppercase tracking-wider">Intrinsic Value</p>
            <p className="text-3xl font-extrabold text-blue-400">
              ₹{intrinsic.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            </p>
            <p className="text-xs text-gray-500">DCF per share</p>
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      {/* ── OVERVIEW ─────────────────────────────────────────────────────── */}
      {tab === "overview" && (
        <div className="space-y-8">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            <StatCard label="ROE" value={fmt(roe, "", "%")} sub="Return on Equity" color="blue" />
            <StatCard label="ROCE" value={fmt(roce, "", "%")} sub="Return on Capital" color="green" />
            <StatCard label="Net Margin" value={fmt(npm, "", "%")} sub="Net Profit Margin" color="blue" />
            <StatCard label="Current Ratio" value={fmt(cr, "", "x")} sub="Liquidity" color="green" />
            <StatCard label="Debt / Equity" value={fmt(de, "", "x")} sub="Leverage" color="amber" />
            <StatCard label="Interest Coverage" value={fmt(ic, "", "x")} sub="Solvency" color="green" />
            {intrinsic && <StatCard label="Intrinsic Value" value={fmt(intrinsic, "₹", "", 0)} sub="DCF per share" color="blue" />}
            {mc?.p50 && <StatCard label="MC Median" value={fmt(mc.p50, "₹", "", 0)} sub="Monte Carlo P50" color="green" />}
          </div>

          {/* Revenue + Net Income trend */}
          <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5">
            <TrendChart
              table={statements.income_statement}
              metrics={["Sales", "Net Profit"]}
              title="Revenue vs Net Profit (₹ Cr)"
              colors={["#3b82f6", "#10b981"]}
            />
          </div>

          {/* Profitability trend */}
          {ratios?.Profitability && (
            <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5">
              <TrendChart
                table={ratios.Profitability}
                metrics={["Return on Equity % (ROE)", "Return on Capital Employed % (ROCE)", "Net Profit Margin (%)"]}
                title="Profitability Trend (%)"
                colors={["#3b82f6", "#10b981", "#f59e0b"]}
              />
            </div>
          )}

          {/* AI Summary teaser */}
          {ai_commentary?.thesis?.executive_summary && (
            <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5">
              <p className="text-xs text-blue-400 uppercase tracking-wider font-semibold mb-2">AI Investment Summary</p>
              <p className="text-gray-300 text-sm leading-relaxed">{ai_commentary.thesis.executive_summary}</p>
              <button onClick={() => setTab("ai")} className="text-xs text-blue-400 mt-2 hover:underline">
                Full AI Analysis →
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── STATEMENTS ───────────────────────────────────────────────────── */}
      {tab === "statements" && (
        <div className="space-y-10">
          <FinancialTable
            table={statements.income_statement}
            title="Income Statement (₹ Cr)"
            highlightRows={["Sales", "Operating Profit", "Net Profit"]}
          />
          <FinancialTable
            table={statements.balance_sheet}
            title="Balance Sheet (₹ Cr)"
            highlightRows={["Total Assets", "Total Liabilities", "Shareholder Funds"]}
          />
          <FinancialTable
            table={statements.cash_flow}
            title="Cash Flow Statement (₹ Cr)"
            highlightRows={["Cash from Operating Activity", "Net Cash Flow"]}
          />
        </div>
      )}

      {/* ── RATIOS ───────────────────────────────────────────────────────── */}
      {tab === "ratios" && (
        <div className="space-y-10">
          {Object.entries(ratios).map(([category, table]) => (
            <div key={category}>
              <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5 mb-4">
                <TrendChart
                  table={table}
                  metrics={table.rows.slice(0, 3).map((r) => String(r.metric))}
                  title={`${category} Ratios — Trend`}
                />
              </div>
              <FinancialTable table={table} title={`${category} Ratios`} compact />
            </div>
          ))}
        </div>
      )}

      {/* ── DUPONT + COMMON SIZE ─────────────────────────────────────────── */}
      {tab === "dupont" && (
        <div className="space-y-10">
          <div>
            <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5 mb-4">
              <TrendChart
                table={dupont}
                metrics={["DuPont ROE (%)  [Product of above x 100]", "Direct ROE (%)  [NI / Avg Equity x 100]"]}
                title="DuPont ROE — Derived vs Direct"
                colors={["#3b82f6", "#10b981"]}
              />
            </div>
            <FinancialTable table={dupont} title="DuPont Decomposition" highlightRows={["DuPont ROE (%)  [Product of above x 100]"]} />
          </div>
          <FinancialTable
            table={common_size.income_statement}
            title="Common Size Income Statement (% of Revenue)"
            highlightRows={["Operating Profit", "Net Profit"]}
            compact
          />
          <FinancialTable
            table={common_size.balance_sheet}
            title="Common Size Balance Sheet (% of Total Assets)"
            highlightRows={["Total Assets"]}
            compact
          />
        </div>
      )}

      {/* ── SCHEDULES ────────────────────────────────────────────────────── */}
      {tab === "schedules" && (
        <div className="space-y-10">
          <div>
            <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5 mb-4">
              <TrendChart
                table={schedules.working_capital}
                metrics={["Net Working Capital (₹ Cr)", "Cash Conversion Cycle (days)"]}
                title="Working Capital Trend"
                colors={["#3b82f6", "#f59e0b"]}
              />
            </div>
            <FinancialTable
              table={schedules.working_capital}
              title="Working Capital Schedule (₹ Cr)"
              highlightRows={["Net Working Capital (₹ Cr)", "Cash Conversion Cycle (days)"]}
            />
          </div>
          <div>
            <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5 mb-4">
              <TrendChart
                table={schedules.debt}
                metrics={["Net Debt (₹ Cr)", "Interest Coverage - EBIT (x)"]}
                title="Debt Profile Trend"
                colors={["#ef4444", "#10b981"]}
              />
            </div>
            <FinancialTable
              table={schedules.debt}
              title="Debt Schedule (₹ Cr)"
              highlightRows={["Net Debt (₹ Cr)", "Interest Coverage - EBIT (x)"]}
            />
          </div>
        </div>
      )}

      {/* ── FORECASTS ────────────────────────────────────────────────────── */}
      {tab === "forecasts" && (
        <div className="space-y-10">
          {Object.keys(forecasts.scenarios).length === 0 ? (
            <p className="text-gray-500">Forecasts not generated (run without --no-forecast).</p>
          ) : (
            <>
              {/* Scenario selector */}
              {(["base", "bull", "bear"] as const).map((s) => {
                const tbl = forecasts.scenarios[s];
                if (!tbl?.rows?.length) return null;
                const color = s === "bull" ? "#10b981" : s === "bear" ? "#ef4444" : "#3b82f6";
                const label = s.charAt(0).toUpperCase() + s.slice(1);
                return (
                  <div key={s}>
                    <h3 className="text-base font-semibold mb-3" style={{ color }}>
                      {label} Scenario Forecast
                    </h3>
                    <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5 mb-4">
                      <TrendChart
                        table={tbl}
                        metrics={["Revenue", "Net Income", "Free Cash Flow"]}
                        title={`${label} — Revenue, Net Income & FCF (₹ Cr)`}
                        colors={[color, "#94a3b8", "#f59e0b"]}
                      />
                    </div>
                    <FinancialTable table={tbl} title={`${label} Scenario (₹ Cr)`} compact
                      highlightRows={["Revenue", "Net Income", "Free Cash Flow"]} />
                  </div>
                );
              })}
            </>
          )}
        </div>
      )}

      {/* ── DCF VALUATION ────────────────────────────────────────────────── */}
      {tab === "valuation" && (
        <div className="space-y-10">
          {!dcf?.valuation?.intrinsic_value_per_share ? (
            <p className="text-gray-500">DCF data not available.</p>
          ) : (
            <>
              {/* Valuation cards */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                <StatCard label="Intrinsic Value / Share" value={fmt(intrinsic, "₹", "", 0)} color="blue" />
                <StatCard label="Enterprise Value" value={fmt(dcf.valuation.enterprise_value_cr, "₹", " Cr", 0)} color="green" />
                <StatCard label="Equity Value" value={fmt(dcf.valuation.equity_value_cr, "₹", " Cr", 0)} color="blue" />
                <StatCard label="Net Debt" value={fmt(dcf.valuation.net_debt_cr, "₹", " Cr", 0)} color="amber" />
                <StatCard label="Sum of PV FCF" value={fmt(dcf.valuation.sum_pv_fcf_cr, "₹", " Cr", 0)} color="green" />
                <StatCard label="PV Terminal Value" value={fmt(dcf.valuation.pv_terminal_value_cr, "₹", " Cr", 0)} color="blue" />
                <StatCard label="WACC" value={fmt(dcf.wacc_used ? dcf.wacc_used * 100 : null, "", "%")} color="amber" />
                <StatCard label="FCF Growth" value={fmt(dcf.fcf_growth_used, "", "%")} color="green" />
              </div>

              {/* Assumptions */}
              {dcf.assumptions && (
                <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5">
                  <h3 className="text-base font-semibold text-white mb-3">DCF Assumptions</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-2 gap-x-6 text-sm">
                    {Object.entries(dcf.assumptions).map(([k, v]) => (
                      <div key={k} className="flex justify-between border-b border-gray-800 pb-1">
                        <span className="text-gray-400">{k}</span>
                        <span className="text-white font-medium">{String(v ?? "—")}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Projected FCF Table */}
              {dcf.projections?.rows?.length > 0 && (
                <div>
                  <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5 mb-4">
                    <TrendChart
                      table={dcf.projections}
                      metrics={["Projected FCF (₹ Cr)", "PV of FCF (₹ Cr)"]}
                      title="Projected FCF vs Present Value (₹ Cr)"
                      colors={["#3b82f6", "#10b981"]}
                    />
                  </div>
                  <FinancialTable table={dcf.projections} title="DCF Projections" />
                </div>
              )}

              {/* WACC breakdown */}
              {forecasts.wacc?.wacc && (
                <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5">
                  <h3 className="text-base font-semibold text-white mb-3">WACC Breakdown (CAPM)</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                    <StatCard label="WACC" value={fmt(forecasts.wacc.wacc ? forecasts.wacc.wacc * 100 : null, "", "%")} color="blue" />
                    <StatCard label="Cost of Equity" value={fmt(forecasts.wacc.cost_of_equity ? forecasts.wacc.cost_of_equity * 100 : null, "", "%")} color="green" />
                    <StatCard label="Cost of Debt" value={fmt(forecasts.wacc.cost_of_debt ? forecasts.wacc.cost_of_debt * 100 : null, "", "%")} color="amber" />
                    <StatCard label="Beta" value={fmt(forecasts.wacc.beta, "", ` (${forecasts.wacc.beta_source})`)} color="blue" />
                  </div>
                  {forecasts.wacc.computation_log?.length > 0 && (
                    <div className="bg-gray-900 rounded-lg p-3 font-mono text-xs text-gray-400 space-y-0.5 max-h-40 overflow-y-auto">
                      {forecasts.wacc.computation_log.map((l, i) => <p key={i}>{l}</p>)}
                    </div>
                  )}
                </div>
              )}

              {/* Sensitivity Heatmap */}
              {forecasts.sensitivity?.table?.rows?.length > 0 && (
                <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5">
                  <SensitivityHeatmap data={forecasts.sensitivity} intrinsic={intrinsic} />
                </div>
              )}

              {/* Monte Carlo */}
              {mc?.p50 && (
                <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5">
                  <h3 className="text-base font-semibold text-white mb-4">Monte Carlo Simulation ({mc.n_simulations?.toLocaleString()} runs)</h3>
                  <MonteCarloChart data={mc} />
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── AI INSIGHTS ──────────────────────────────────────────────────── */}
      {tab === "ai" && <AIInsights data={ai_commentary} />}

      {/* ── AUDIT ────────────────────────────────────────────────────────── */}
      {tab === "audit" && (
        <div className="space-y-8">
          {/* Data shape */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard label="Canonical Metrics" value={String(audit.data_shape.canonical_rows)} color="blue" />
            <StatCard label="Years of Data" value={String(audit.data_shape.canonical_cols)} color="green" />
            <StatCard label="Ratios Computed" value={String(audit.data_shape.ratio_rows)} color="blue" />
            <StatCard
              label="Integrity Score"
              value={`${audit.anomaly_detection?.summary?.integrity_score ?? "—"}%`}
              color={Number(audit.anomaly_detection?.summary?.integrity_score) >= 90 ? "green" : "amber"}
            />
          </div>

          {/* Anomaly flags */}
          <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5">
            <h3 className="text-base font-semibold text-white mb-3">Anomaly Detection Report</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 text-sm">
              {Object.entries(audit.anomaly_detection?.summary ?? {}).map(([k, v]) => (
                <div key={k} className="bg-gray-900 rounded-lg p-2">
                  <p className="text-gray-500 text-xs">{k.replace(/_/g, " ")}</p>
                  <p className="text-white font-semibold">{String(v)}</p>
                </div>
              ))}
            </div>
            {audit.anomaly_detection?.flags?.length > 0 ? (
              <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                {audit.anomaly_detection.flags.map((f, i) => (
                  <div key={i} className="flex gap-3 items-start bg-gray-900 rounded-lg p-3 text-sm">
                    <Badge
                      label={f.severity}
                      variant={f.severity === "ERROR" ? "red" : f.severity === "WARNING" ? "amber" : "muted"}
                    />
                    <div>
                      <span className="text-white font-medium">{f.metric}</span>
                      <span className="text-gray-500 mx-2">·</span>
                      <span className="text-gray-400">{f.year}</span>
                      <span className="text-gray-500 mx-2">·</span>
                      <span className="text-amber-400 font-mono text-xs">{f.method}</span>
                      <p className="text-xs text-gray-400 mt-0.5">{f.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-emerald-400 text-sm">No anomalies detected.</p>
            )}
          </div>

          {/* Industry classification */}
          {audit.industry_classification?.sector && (
            <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5">
              <h3 className="text-base font-semibold text-white mb-3">Industry Classification</h3>
              <div className="flex gap-4 flex-wrap mb-4">
                <StatCard label="Sector" value={audit.industry_classification.sector} color="blue" />
                <StatCard label="Confidence" value={fmt(audit.industry_classification.confidence ? audit.industry_classification.confidence * 100 : null, "", "%")} color="green" />
              </div>
              <p className="text-sm text-gray-400 mb-2">Peers: {audit.industry_classification.peers?.join(", ")}</p>
              {Object.keys(audit.industry_classification.peer_medians ?? {}).length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Peer Median Benchmarks</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                    {Object.entries(audit.industry_classification.peer_medians).map(([k, v]) => (
                      <div key={k} className="bg-gray-900 rounded p-2 flex justify-between">
                        <span className="text-gray-400">{k}</span>
                        <span className="text-white font-medium">{typeof v === "number" ? v.toFixed(2) : v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
