"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FinancialData } from "@/types/financial";
import { fmtCr, fmtNum } from "@/lib/dataUtils";
import SectionCard from "@/components/SectionCard";
import FinTable from "@/components/FinTable";
import { SurfacePlot3D, MonteCarlo3D } from "@/components/Plot3D";
import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

function ValCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div className={`card-sm ${accent ? "border-accent/40 bg-accent/5" : ""}`}>
      <p className="text-xs text-muted uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-xl font-black num ${accent ? "text-accent" : "text-txt"}`}>{value}</p>
      {sub && <p className="text-xs text-muted mt-0.5">{sub}</p>}
    </div>
  );
}

export default function ValuationPage() {
  const { company } = useParams() as { company: string };
  const [data, setData] = useState<FinancialData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/data/${company?.toUpperCase()}_financial_data.json`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [company]);

  if (loading) return <div className="flex items-center justify-center h-64 text-muted animate-pulse">Loading valuation…</div>;
  if (!data?.forecasts?.dcf?.valuation?.intrinsic_value_per_share) {
    return <div className="text-fin-red text-sm">No DCF data. Run the pipeline without --no-forecast.</div>;
  }

  const dcf  = data.forecasts.dcf;
  const wacc = data.forecasts.wacc;
  const mc   = dcf.monte_carlo;
  const val  = dcf.valuation;
  const sens = data.forecasts.sensitivity;

  // Build 3D surface data from sensitivity table
  const rowVals  = sens?.row_values ?? [];
  const colVals  = sens?.col_values ?? [];
  const zMatrix: (number | null)[][] = rowVals.map((row) => {
    const tableRow = sens?.table?.rows?.find((r) => String(r.metric) === row);
    return colVals.map((col) => {
      const v = tableRow?.[col];
      return typeof v === "number" ? v : null;
    });
  });

  // Monte Carlo percentile chart
  const mcData = [
    { label: "P10", value: mc?.p10, color: "#ff3d57" },
    { label: "P25", value: mc?.p25, color: "#ffb020" },
    { label: "P50", value: mc?.p50, color: "#3b7cf4" },
    { label: "P75", value: mc?.p75, color: "#00d68f" },
    { label: "P90", value: mc?.p90, color: "#6ee7b7" },
  ].filter((d) => d.value != null);

  // DCF Bridge waterfall
  const bridgeData = [
    { name: "PV of FCFs",       value: val.sum_pv_fcf_cr,         color: "#3b7cf4" },
    { name: "PV Terminal Value", value: val.pv_terminal_value_cr,  color: "#00d68f" },
    { name: "Enterprise Value",  value: val.enterprise_value_cr,   color: "#6ee7b7" },
    { name: "Less: Net Debt",    value: -(val.net_debt_cr ?? 0),    color: (val.net_debt_cr ?? 0) > 0 ? "#ff3d57" : "#00d68f" },
    { name: "Equity Value",      value: val.equity_value_cr,       color: "#3b7cf4" },
  ].filter((d) => d.value != null);

  return (
    <div className="space-y-8">

      {/* ── Hero Valuation Banner ── */}
      <div className="rounded-xl border border-accent/30 bg-accent/5 p-6">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div>
            <p className="text-xs text-accent uppercase tracking-widest font-semibold mb-1">DCF Intrinsic Value per Share</p>
            <p className="text-6xl font-black text-accent num">
              ₹{val.intrinsic_value_per_share?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            </p>
            <p className="text-sm text-txt2 mt-2">
              Based on WACC {((dcf.wacc_used ?? 0) * 100).toFixed(2)}% · Terminal Growth {dcf.terminal_growth_used}% · FCF Growth {dcf.fcf_growth_used?.toFixed(1)}%
            </p>
          </div>
          <div className="flex gap-3 flex-wrap">
            <div className="card-sm text-center min-w-[110px]">
              <p className="text-xs text-muted mb-0.5">Monte Carlo P50</p>
              <p className="text-xl font-black text-fin-green num">₹{mc?.p50?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</p>
            </div>
            <div className="card-sm text-center min-w-[110px]">
              <p className="text-xs text-muted mb-0.5">Bear (P25)</p>
              <p className="text-xl font-black text-fin-red num">₹{mc?.p25?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</p>
            </div>
            <div className="card-sm text-center min-w-[110px]">
              <p className="text-xs text-muted mb-0.5">Bull (P75)</p>
              <p className="text-xl font-black text-fin-green num">₹{mc?.p75?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Valuation Grid ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <ValCard label="Enterprise Value"    value={fmtCr(val.enterprise_value_cr)}    accent />
        <ValCard label="Equity Value"        value={fmtCr(val.equity_value_cr)} />
        <ValCard label="Net Debt"            value={fmtCr(val.net_debt_cr)} sub={(val.net_debt_cr ?? 0) < 0 ? "Net Cash" : "Net Debt"} />
        <ValCard label="Shares Outstanding"  value={`${val.shares_outstanding_cr?.toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`} />
        <ValCard label="Sum PV of FCFs"      value={fmtCr(val.sum_pv_fcf_cr)} />
        <ValCard label="PV Terminal Value"   value={fmtCr(val.pv_terminal_value_cr)} />
        <ValCard label="Terminal Value"      value={fmtCr(val.terminal_value_cr)} sub="Un-discounted" />
        <ValCard label="TV as % of EV"       value={`${(((val.pv_terminal_value_cr ?? 0) / (val.enterprise_value_cr ?? 1)) * 100).toFixed(1)}%`} sub="Terminal value weight" />
      </div>

      {/* ── DCF Assumptions ── */}
      <SectionCard title="DCF Assumptions">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-y-3 gap-x-6 text-sm">
          {Object.entries(dcf.assumptions ?? {}).map(([k, v]) => (
            <div key={k} className="flex justify-between border-b border-border pb-2">
              <span className="text-muted">{k}</span>
              <span className="font-semibold text-txt num">{String(v ?? "—")}</span>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* ── DCF Bridge ── */}
      <SectionCard title="DCF Value Bridge" subtitle="How equity value is derived from FCF projections">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={bridgeData} margin={{ top: 5, right: 10, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a2d4f" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "#4a6080", fontSize: 11 }} tickLine={false} angle={-25} textAnchor="end" />
            <YAxis tick={{ fill: "#4a6080", fontSize: 10 }} tickLine={false} axisLine={false}
              tickFormatter={(v) => `₹${(v / 100000).toFixed(1)}L`} width={60} />
            <Tooltip
              contentStyle={{ background: "#0c1529", border: "1px solid #1a2d4f", borderRadius: 8, fontSize: 12 }}
              formatter={(v: number) => [fmtCr(v), ""]}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {bridgeData.map((d, i) => <Cell key={i} fill={d.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </SectionCard>

      {/* ── FCF Projections Table ── */}
      {dcf.projections?.rows?.length > 0 && (
        <SectionCard title="Projected FCF Schedule">
          <FinTable table={dcf.projections} />
        </SectionCard>
      )}

      {/* ── WACC Breakdown ── */}
      {wacc?.wacc && (
        <SectionCard title="WACC Breakdown — CAPM" subtitle={`Beta: ${wacc.beta?.toFixed(2)} (${wacc.beta_source})`}>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <ValCard label="WACC"          value={`${((wacc.wacc ?? 0) * 100).toFixed(2)}%`} accent />
            <ValCard label="Cost of Equity" value={`${((wacc.cost_of_equity ?? 0) * 100).toFixed(2)}%`} />
            <ValCard label="Cost of Debt"   value={`${((wacc.cost_of_debt ?? 0) * 100).toFixed(2)}%`} />
            <ValCard label="Debt Weight"    value={`${((wacc.debt_weight ?? 0) * 100).toFixed(1)}%`} />
          </div>
          {wacc.computation_log?.length > 0 && (
            <div className="rounded-lg border border-border bg-surface2 p-3 font-mono text-xs text-txt2 space-y-0.5 max-h-36 overflow-y-auto">
              {wacc.computation_log.map((l, i) => <p key={i}>{l}</p>)}
            </div>
          )}
        </SectionCard>
      )}

      {/* ── 3D Sensitivity Surface ── */}
      {zMatrix.length > 0 && (
        <SectionCard title="3D Sensitivity Surface" subtitle="WACC × Terminal Growth Rate → Intrinsic Value per Share (₹) · Drag to rotate">
          <SurfacePlot3D
            xVals={colVals}
            yVals={rowVals}
            zMatrix={zMatrix}
            title=""
            xTitle="Terminal Growth Rate"
            yTitle="WACC"
            zTitle="₹ / Share"
            highlightZ={val.intrinsic_value_per_share ?? undefined}
          />
          <p className="text-xs text-muted mt-2 text-center">
            Green = above base · Red = below base · Drag to rotate, scroll to zoom
          </p>
        </SectionCard>
      )}

      {/* ── Monte Carlo 2D Percentiles ── */}
      {mc?.p50 && (
        <SectionCard title="Monte Carlo Simulation" subtitle={`${mc.n_simulations?.toLocaleString()} simulations · WACC and TGR sampled from normal distributions`}>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
            {mcData.map((d) => (
              <div key={d.label} className="card-sm text-center">
                <p className="text-xs text-muted mb-1">{d.label}</p>
                <p className={`text-lg font-black num ${d.label === "P10" ? "text-fin-red" : d.label === "P90" ? "text-fin-green" : d.label === "P50" ? "text-accent" : d.label === "P75" ? "text-fin-green" : "text-fin-amber"}`}>₹{d.value?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-4">
            <div>
              <p className="text-xs text-muted uppercase tracking-wider mb-3">Percentile Distribution</p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={mcData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a2d4f" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: "#4a6080", fontSize: 12 }} tickLine={false} />
                  <YAxis tick={{ fill: "#4a6080", fontSize: 11 }} tickLine={false} axisLine={false}
                    tickFormatter={(v) => `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} width={60} />
                  <Tooltip
                    contentStyle={{ background: "#0c1529", border: "1px solid #1a2d4f", borderRadius: 8, fontSize: 12 }}
                    formatter={(v: number) => [`₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`, "Value"]}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {mcData.map((d, i) => <Cell key={i} fill={d.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col gap-3 justify-center">
              <div className="card-sm">
                <p className="text-xs text-muted uppercase tracking-wider mb-2">Key Statistics</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-muted">Mean</span><span className="num font-semibold text-txt">₹{mc.mean?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</span></div>
                  <div className="flex justify-between"><span className="text-muted">Std Deviation</span><span className="num font-semibold text-txt">₹{mc.std?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</span></div>
                  <div className="flex justify-between"><span className="text-muted">Most likely range</span><span className="num font-semibold text-accent">₹{mc.p25?.toLocaleString("en-IN", { maximumFractionDigits: 0 })} – ₹{mc.p75?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</span></div>
                  <div className="flex justify-between border-t border-border pt-2"><span className="text-muted">Prob within ±20% of median</span><span className="font-black text-fin-green num">{mc.prob_within_20?.toFixed(1)}%</span></div>
                </div>
              </div>
            </div>
          </div>

          {/* 3D Monte Carlo */}
          <div className="border-t border-border pt-4 mt-4">
            <p className="text-xs text-muted uppercase tracking-wider mb-1">3D Probability Distribution — Intrinsic Value × WACC</p>
            <p className="text-xs text-muted mb-3">Simulated distribution showing how intrinsic value shifts across WACC levels · Drag to rotate</p>
            <MonteCarlo3D
              p10={mc.p10} p25={mc.p25} p50={mc.p50}
              p75={mc.p75} p90={mc.p90}
              mean={mc.mean} std={mc.std}
            />
          </div>
        </SectionCard>
      )}

      {/* ── 2D Sensitivity Table ── */}
      {sens?.table?.rows?.length > 0 && (
        <SectionCard title="Sensitivity Table" subtitle="Intrinsic Value per Share (₹) across WACC × Terminal Growth combinations">
          <FinTable table={sens.table} />
          <p className="text-xs text-muted mt-3">
            Base case: WACC {((dcf.wacc_used ?? 0) * 100).toFixed(1)}% · Terminal Growth {dcf.terminal_growth_used}% → <span className="text-accent font-semibold num">₹{val.intrinsic_value_per_share?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</span>
          </p>
        </SectionCard>
      )}
    </div>
  );
}
