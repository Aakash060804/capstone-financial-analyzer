"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FinancialData } from "@/types/financial";
import { fmtCr, getLastValue } from "@/lib/dataUtils";
import SectionCard from "@/components/SectionCard";
import FinTable from "@/components/FinTable";

function DownloadBtn({ href, label, sub, icon }: { href: string; label: string; sub: string; icon: string }) {
  return (
    <a
      href={href}
      download
      className="flex items-center gap-4 rounded-xl border border-border bg-surface2 hover:border-accent/50 hover:bg-accent/5 p-4 transition-all group"
    >
      <div className="text-3xl w-12 h-12 flex items-center justify-center rounded-lg bg-accent/10 group-hover:bg-accent/20 transition-colors">
        {icon}
      </div>
      <div>
        <p className="text-sm font-bold text-txt group-hover:text-accent transition-colors">{label}</p>
        <p className="text-xs text-muted mt-0.5">{sub}</p>
      </div>
      <div className="ml-auto">
        <svg className="w-4 h-4 text-muted group-hover:text-accent transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
      </div>
    </a>
  );
}

export default function ReportsPage() {
  const { company } = useParams() as { company: string };
  const slug = company?.toUpperCase() ?? "";
  const [data, setData] = useState<FinancialData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/data/${slug}_financial_data.json`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [slug]);

  if (loading) return <div className="flex items-center justify-center h-64 text-muted animate-pulse">Loading reports…</div>;
  if (!data) return <div className="text-fin-red text-sm">No data. Run the pipeline first.</div>;

  const sc = data.forecasts.scenarios;
  const hasScenarios = sc?.base?.rows?.length > 0;
  const forecastYears = sc?.base?.headers?.filter((h) => h !== "metric") ?? [];
  const lastFY = forecastYears[forecastYears.length - 1];

  const dcf = data.forecasts.dcf;
  const val = dcf?.valuation;

  return (
    <div className="space-y-8">

      {/* ── Downloads ── */}
      <SectionCard title="Download Reports" subtitle="Export full analysis to Excel or raw JSON">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <DownloadBtn
            href={`/data/${slug}_Financial_Analysis.xlsx`}
            label={`${slug} — Full Excel Report`}
            sub="9-sheet workbook: Statements · Ratios · DuPont · Forecasts · DCF · AI Commentary"
            icon="📊"
          />
          <DownloadBtn
            href={`/data/${slug}_financial_data.json`}
            label={`${slug} — Raw JSON Data`}
            sub="Complete structured data used to power this dashboard"
            icon="📄"
          />
        </div>

        {/* How to regenerate */}
        <div className="mt-6 rounded-lg border border-border bg-surface2 p-4">
          <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Regenerate Reports</p>
          <pre className="text-xs text-txt2 overflow-x-auto leading-relaxed">{`cd financial_analyzer
python main.py --company ${slug}
cp outputs/${slug}_financial_data.json ../webapp/public/data/
cp outputs/${slug}_Financial_Analysis.xlsx ../webapp/public/data/`}</pre>
        </div>
      </SectionCard>

      {/* ── Data Summary ── */}
      <SectionCard title="Report Summary" subtitle="What's included in this analysis">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Historical Years",  value: (data.statements.income_statement.headers.filter(h => h !== "metric" && h !== "TTM").length).toString(), sub: "Income / BS / CF" },
            { label: "Ratio Metrics",     value: Object.values(data.ratios).reduce((a, t) => a + t.rows.length, 0).toString(), sub: "Across 6 categories" },
            { label: "Forecast Scenarios", value: "3", sub: "Bear · Base · Bull" },
            { label: "MC Simulations",    value: dcf?.monte_carlo?.n_simulations?.toLocaleString() ?? "—", sub: "Monte Carlo runs" },
          ].map((s) => (
            <div key={s.label} className="card-sm">
              <p className="text-xs text-muted uppercase tracking-wider mb-1">{s.label}</p>
              <p className="text-2xl font-black text-txt num">{s.value}</p>
              <p className="text-xs text-muted mt-0.5">{s.sub}</p>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* ── Valuation Summary ── */}
      {val?.intrinsic_value_per_share && (
        <SectionCard title="DCF Valuation Summary" subtitle="Key outputs from the discounted cash flow model">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="card-sm border-accent/30 bg-accent/5 col-span-2 sm:col-span-1">
              <p className="text-xs text-accent uppercase tracking-wider mb-1">Intrinsic Value / Share</p>
              <p className="text-3xl font-black text-accent num">₹{val.intrinsic_value_per_share?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</p>
            </div>
            <div className="card-sm">
              <p className="text-xs text-muted uppercase tracking-wider mb-1">Enterprise Value</p>
              <p className="text-xl font-bold text-txt num">{fmtCr(val.enterprise_value_cr)}</p>
            </div>
            <div className="card-sm">
              <p className="text-xs text-muted uppercase tracking-wider mb-1">Equity Value</p>
              <p className="text-xl font-bold text-txt num">{fmtCr(val.equity_value_cr)}</p>
            </div>
            <div className="card-sm">
              <p className="text-xs text-muted uppercase tracking-wider mb-1">WACC Used</p>
              <p className="text-xl font-bold text-txt num">{((dcf.wacc_used ?? 0) * 100).toFixed(2)}%</p>
            </div>
            <div className="card-sm">
              <p className="text-xs text-muted uppercase tracking-wider mb-1">Terminal Growth</p>
              <p className="text-xl font-bold text-txt num">{dcf.terminal_growth_used}%</p>
            </div>
            <div className="card-sm">
              <p className="text-xs text-muted uppercase tracking-wider mb-1">Monte Carlo P50</p>
              <p className="text-xl font-bold text-fin-green num">₹{dcf.monte_carlo?.p50?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</p>
            </div>
          </div>
        </SectionCard>
      )}

      {/* ── Forecast Tables ── */}
      {hasScenarios && (
        <>
          {(["base", "bull", "bear"] as const).map((key) => {
            const tbl = (sc as Record<string, typeof sc.base>)[key];
            const colors = { base: "text-accent", bull: "text-fin-green", bear: "text-fin-red" };
            const labels = { base: "Base Case", bull: "Bull Case", bear: "Bear Case" };
            if (!tbl?.rows?.length) return null;
            return (
              <SectionCard
                key={key}
                title={`${labels[key]} — Complete Forecast`}
                subtitle={`All metrics · ${forecastYears[0]} to ${lastFY}`}
              >
                <p className="text-xs text-muted mb-3">
                  Revenue CAGR assumption ·{" "}
                  <span className={`font-semibold ${colors[key]}`}>{labels[key]}</span>
                </p>
                <FinTable
                  table={tbl}
                  highlightRows={["Revenue", "Net Income", "Free Cash Flow", "OPM %", "FCF Margin (%)"]}
                />
              </SectionCard>
            );
          })}

          {/* DCF Projections */}
          {dcf?.projections?.rows?.length > 0 && (
            <SectionCard title="DCF — FCF Projection Schedule" subtitle="Projected free cash flows used in the valuation">
              <FinTable table={dcf.projections} highlightRows={["Free Cash Flow", "PV of FCF"]} />
            </SectionCard>
          )}
        </>
      )}

      {/* ── AI Commentary ── */}
      {data.ai_commentary?.thesis && (
        <SectionCard title="AI Investment Thesis" subtitle="Generated by Claude AI — research purposes only, not investment advice">
          <div className="rounded-lg border border-border bg-surface2 p-4 mb-4">
            <p className="text-sm text-txt2 leading-relaxed">{data.ai_commentary.thesis.executive_summary}</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-wider text-fin-green mb-2">Key Strengths</p>
              <ul className="space-y-1">
                {data.ai_commentary.thesis.key_strengths?.map((s, i) => (
                  <li key={i} className="text-xs text-txt2 flex gap-2"><span className="text-fin-green mt-0.5">✓</span>{s}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs font-black uppercase tracking-wider text-fin-red mb-2">Key Concerns</p>
              <ul className="space-y-1">
                {data.ai_commentary.thesis.key_concerns?.map((c, i) => (
                  <li key={i} className="text-xs text-txt2 flex gap-2"><span className="text-fin-red mt-0.5">✗</span>{c}</li>
                ))}
              </ul>
            </div>
          </div>
        </SectionCard>
      )}

      {/* ── Disclaimer ── */}
      <div className="rounded-xl border border-fin-amber/20 bg-fin-amber/5 p-4">
        <p className="text-xs font-semibold text-fin-amber uppercase tracking-wider mb-1">Disclaimer</p>
        <p className="text-xs text-txt2 leading-relaxed">
          This analysis is generated by an automated pipeline for educational and research purposes only.
          It does not constitute investment advice. Financial data is sourced from Screener.in and may contain
          errors or omissions. Always consult a SEBI-registered investment advisor before making investment decisions.
          Past performance is not indicative of future results.
        </p>
      </div>
    </div>
  );
}
