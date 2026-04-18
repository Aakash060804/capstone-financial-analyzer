import { FinancialData, DataTable } from "@/types/financial";

// ─── primitive helpers ────────────────────────────────────────────────────────

export function getYears(table: DataTable, excludeTTM = true): string[] {
  return table.headers
    .filter((h) => h !== "metric" && (!excludeTTM || h !== "TTM"))
    .sort();
}

export function getValue(
  table: DataTable,
  metric: string,
  year: string
): number | null {
  const row = table.rows.find((r) => String(r.metric) === metric);
  if (!row) return null;
  const v = row[year];
  return typeof v === "number" ? v : null;
}

export function getLastValue(table: DataTable, metric: string): number | null {
  const years = getYears(table);
  for (let i = years.length - 1; i >= 0; i--) {
    const v = getValue(table, metric, years[i]);
    if (v !== null && !isNaN(v)) return v;
  }
  return null;
}

export function getLastYear(table: DataTable): string {
  const years = getYears(table);
  for (let i = years.length - 1; i >= 0; i--) {
    const row = table.rows[0];
    if (row && row[years[i]] !== null) return years[i];
  }
  return years[years.length - 1];
}

// returns last two years that have non-null values for a given metric
export function getLastTwo(
  table: DataTable,
  metric: string
): { current: number | null; prev: number | null; currYear: string; prevYear: string } {
  const years = getYears(table);
  const vals: { year: string; val: number }[] = [];
  for (const y of years) {
    const v = getValue(table, metric, y);
    if (v !== null && !isNaN(v)) vals.push({ year: y, val: v });
  }
  const current = vals[vals.length - 1] ?? null;
  const prev = vals[vals.length - 2] ?? null;
  return {
    current: current?.val ?? null,
    prev: prev?.val ?? null,
    currYear: current?.year ?? "",
    prevYear: prev?.year ?? "",
  };
}

// ─── growth ──────────────────────────────────────────────────────────────────

export function yoyGrowth(current: number | null, prev: number | null): number | null {
  if (current === null || prev === null || prev === 0) return null;
  return ((current - prev) / Math.abs(prev)) * 100;
}

export function cagr(first: number | null, last: number | null, years: number): number | null {
  if (!first || !last || years <= 0 || first <= 0) return null;
  return (Math.pow(last / first, 1 / years) - 1) * 100;
}

// ─── series extraction ────────────────────────────────────────────────────────

export function getSeries(
  table: DataTable,
  metric: string,
  excludeTTM = true
): { year: string; value: number | null }[] {
  return getYears(table, excludeTTM).map((y) => ({
    year: y,
    value: getValue(table, metric, y),
  }));
}

// ─── combined historical + forecast chart data ────────────────────────────────
// Merges 11 years of actuals with 5-year bear/base/bull forecasts on one timeline

export function buildCombinedSeries(
  data: FinancialData,
  historicMetric: string,   // e.g. "Sales" from income_statement
  forecastMetric: string    // e.g. "Revenue" from scenarios
): {
  year: string;
  historical: number | null;
  base: number | null;
  bull: number | null;
  bear: number | null;
}[] {
  const inc = data.statements.income_statement;
  const histYears = getYears(inc);
  const scenarios = data.forecasts.scenarios;

  // historical points
  const result: Record<
    string,
    { historical: number | null; base: number | null; bull: number | null; bear: number | null }
  > = {};

  for (const y of histYears) {
    const v = getValue(inc, historicMetric, y);
    result[y] = { historical: v, base: null, bull: null, bear: null };
  }

  // bridge: last historical year also starts the forecast lines
  const lastHistYear = histYears[histYears.length - 1];
  const bridgeVal = result[lastHistYear]?.historical ?? null;

  // forecast points
  const forecastYears =
    scenarios.base?.headers.filter((h) => h !== "metric") ?? [];

  for (const fy of forecastYears) {
    const baseV = getValue(scenarios.base, forecastMetric, fy);
    const bullV = getValue(scenarios.bull, forecastMetric, fy);
    const bearV = getValue(scenarios.bear, forecastMetric, fy);
    result[fy] = { historical: null, base: baseV, bull: bullV, bear: bearV };
  }

  // insert bridge point so lines connect seamlessly
  if (bridgeVal !== null && forecastYears.length > 0) {
    result[lastHistYear] = {
      historical: bridgeVal,
      base: bridgeVal,
      bull: bridgeVal,
      bear: bridgeVal,
    };
  }

  return Object.entries(result)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([year, vals]) => ({ year, ...vals }));
}

// ─── derived KPIs ─────────────────────────────────────────────────────────────

export interface SnapshotKPI {
  label: string;
  value: number | null;
  unit: string;
  yoy: number | null;
  year: string;
  prevYear: string;
  format: "crore" | "percent" | "ratio" | "rs";
}

export function buildSnapshotKPIs(data: FinancialData): SnapshotKPI[] {
  const inc = data.statements.income_statement;
  const cf = data.statements.cash_flow;

  const mk = (
    label: string,
    table: DataTable,
    metric: string,
    unit: string,
    format: SnapshotKPI["format"]
  ): SnapshotKPI => {
    const { current, prev, currYear, prevYear } = getLastTwo(table, metric);
    return {
      label,
      value: current,
      unit,
      yoy: yoyGrowth(current, prev),
      year: currYear,
      prevYear,
      format,
    };
  };

  return [
    mk("Revenue", inc, "Sales", "₹ Cr", "crore"),
    mk("Net Profit", inc, "Net Profit", "₹ Cr", "crore"),
    mk("Operating Profit", inc, "Operating Profit", "₹ Cr", "crore"),
    mk("OPM %", inc, "OPM %", "%", "percent"),
    mk("Free Cash Flow", cf, "Free Cash Flow", "₹ Cr", "crore"),
    mk("Net Cash Flow", cf, "Net Cash Flow", "₹ Cr", "crore"),
    mk("EPS", inc, "EPS in Rs", "₹", "rs"),
    mk("CFO", cf, "Cash from Operating Activity", "₹ Cr", "crore"),
  ];
}

// ─── derived insight cards ────────────────────────────────────────────────────

export interface DerivedInsight {
  title: string;
  value: string;
  description: string;
  signal: "positive" | "negative" | "neutral";
}

export function buildDerivedInsights(data: FinancialData): DerivedInsight[] {
  const inc = data.statements.income_statement;
  const cf = data.statements.cash_flow;
  const years = getYears(inc);

  // Revenue CAGR (10-year)
  const revFirst = getValue(inc, "Sales", years[0]);
  const revLast = getLastValue(inc, "Sales");
  const revCagr = cagr(revFirst, revLast, years.length - 1);

  // FCF Conversion (FCF / Net Profit)
  const fcf = getLastValue(cf, "Free Cash Flow");
  const np = getLastValue(inc, "Net Profit");
  const fcfConv = fcf && np ? (fcf / np) * 100 : null;

  // Operating leverage = ΔOp Profit% / ΔRevenue%
  const { current: opCurr, prev: opPrev } = getLastTwo(inc, "Operating Profit");
  const { current: revCurr, prev: revPrev } = getLastTwo(inc, "Sales");
  const opGrowth = yoyGrowth(opCurr, opPrev);
  const revGrowth = yoyGrowth(revCurr, revPrev);
  const opLeverage =
    opGrowth !== null && revGrowth !== null && revGrowth !== 0
      ? opGrowth / revGrowth
      : null;

  // EPS CAGR
  const epsFirst = getValue(inc, "EPS in Rs", years[0]);
  const epsLast = getLastValue(inc, "EPS in Rs");
  const epsCagr = cagr(epsFirst, epsLast, years.length - 1);

  // Profit CAGR
  const npFirst = getValue(inc, "Net Profit", years[0]);
  const npCagr = cagr(npFirst, np, years.length - 1);

  const insights: DerivedInsight[] = [];

  if (revCagr !== null) {
    insights.push({
      title: `${(years.length - 1)}-Year Revenue CAGR`,
      value: `${revCagr.toFixed(1)}%`,
      description: `Revenue compounded at ${revCagr.toFixed(1)}% annually since ${years[0]}`,
      signal: revCagr >= 10 ? "positive" : revCagr >= 5 ? "neutral" : "negative",
    });
  }

  if (fcfConv !== null) {
    insights.push({
      title: "FCF Conversion Rate",
      value: `${fcfConv.toFixed(0)}%`,
      description:
        fcfConv >= 100
          ? "FCF exceeds net profit — high earnings quality"
          : fcfConv >= 75
          ? "Strong cash conversion from reported profits"
          : "Cash conversion below profits — monitor working capital",
      signal: fcfConv >= 90 ? "positive" : fcfConv >= 60 ? "neutral" : "negative",
    });
  }

  if (opLeverage !== null) {
    insights.push({
      title: "Operating Leverage",
      value: `${opLeverage.toFixed(2)}x`,
      description: `Each 1% revenue growth drove ${opLeverage.toFixed(2)}% operating profit growth`,
      signal: opLeverage >= 1.5 ? "positive" : opLeverage >= 0.8 ? "neutral" : "negative",
    });
  }

  if (epsCagr !== null) {
    insights.push({
      title: `EPS CAGR (${years.length - 1}Y)`,
      value: `${epsCagr.toFixed(1)}%`,
      description: `Earnings per share grew at ${epsCagr.toFixed(1)}% annually`,
      signal: epsCagr >= 10 ? "positive" : epsCagr >= 5 ? "neutral" : "negative",
    });
  }

  if (npCagr !== null) {
    insights.push({
      title: `Profit CAGR (${years.length - 1}Y)`,
      value: `${npCagr.toFixed(1)}%`,
      description: `Net profit compounded at ${npCagr.toFixed(1)}% annually`,
      signal: npCagr >= 10 ? "positive" : npCagr >= 5 ? "neutral" : "negative",
    });
  }

  return insights;
}

// ─── scenario derived insights ────────────────────────────────────────────────

export function buildScenarioInsights(
  data: FinancialData
): { label: string; base: string; bull: string; bear: string }[] {
  const sc = data.forecasts.scenarios;
  if (!sc.base?.rows?.length) return [];

  const forecastYears = sc.base.headers.filter((h) => h !== "metric");
  const lastFY = forecastYears[forecastYears.length - 1];
  const firstFY = forecastYears[0];

  const inc = data.statements.income_statement;
  const lastHistRev = getLastValue(inc, "Sales");

  const rev = (s: DataTable) => ({
    last: getValue(s, "Revenue", lastFY),
    first: getValue(s, "Revenue", firstFY),
  });

  const cagrStr = (s: DataTable) => {
    const r = rev(s);
    const c = cagr(lastHistRev, r.last, forecastYears.length);
    return c !== null ? `${c.toFixed(1)}%` : "—";
  };

  const fcfLast = (s: DataTable) => {
    const v = getValue(s, "Free Cash Flow", lastFY);
    return v !== null ? `₹${(v / 1000).toFixed(0)}K Cr` : "—";
  };

  const niLast = (s: DataTable) => {
    const v = getValue(s, "Net Income", lastFY);
    return v !== null ? `₹${(v / 1000).toFixed(0)}K Cr` : "—";
  };

  const opmLast = (s: DataTable) => {
    const v = getValue(s, "OPM %", lastFY);
    return v !== null ? `${v.toFixed(1)}%` : "—";
  };

  return [
    { label: `Revenue by ${lastFY}`, base: `₹${((rev(sc.base).last ?? 0) / 1000).toFixed(0)}K Cr`, bull: `₹${((rev(sc.bull).last ?? 0) / 1000).toFixed(0)}K Cr`, bear: `₹${((rev(sc.bear).last ?? 0) / 1000).toFixed(0)}K Cr` },
    { label: "Revenue CAGR", base: cagrStr(sc.base), bull: cagrStr(sc.bull), bear: cagrStr(sc.bear) },
    { label: `Net Income by ${lastFY}`, base: niLast(sc.base), bull: niLast(sc.bull), bear: niLast(sc.bear) },
    { label: `Free Cash Flow by ${lastFY}`, base: fcfLast(sc.base), bull: fcfLast(sc.bull), bear: fcfLast(sc.bear) },
    { label: `OPM % by ${lastFY}`, base: opmLast(sc.base), bull: opmLast(sc.bull), bear: opmLast(sc.bear) },
  ];
}

// ─── financial health score (0–100) ──────────────────────────────────────────

export function buildHealthScore(data: FinancialData): {
  total: number;
  profitability: number;
  liquidity: number;
  solvency: number;
  growth: number;
  cashFlow: number;
} {
  const score = (val: number | null, good: number, bad: number, higherIsBetter = true) => {
    if (val === null) return 50;
    const ratio = higherIsBetter
      ? Math.min(val / good, 1.5)
      : Math.min(good / val, 1.5);
    return Math.round(Math.min(Math.max(ratio * 100, 0), 100));
  };

  const r = data.ratios;

  const getRatioVal = (cat: string, metricName: string): number | null => {
    const table = (r as Record<string, DataTable>)[cat];
    if (!table) return null;
    return getLastValue(table, metricName);
  };

  const profitability = Math.round(
    (score(getRatioVal("Profitability", "Net Profit Margin (%)"), 15, 0) +
      score(getRatioVal("Profitability", "Return on Equity % (ROE)"), 15, 0) +
      score(getRatioVal("Profitability", "Return on Capital Employed % (ROCE)"), 15, 0)) /
      3
  );

  const liquidity = Math.round(
    (score(getRatioVal("Liquidity", "Current Ratio (x)"), 2, 1) +
      score(getRatioVal("Liquidity", "Quick Ratio (x)"), 1.5, 0.75)) /
      2
  );

  const solvency = Math.round(
    (score(getRatioVal("Solvency", "Debt-to-Equity (x)"), 0.5, 2, false) +
      score(getRatioVal("Solvency", "Interest Coverage (x)"), 10, 2)) /
      2
  );

  const growth = Math.round(
    (score(getRatioVal("Growth", "Revenue Growth (%)"), 15, 0) +
      score(getRatioVal("Growth", "Net Income Growth (%)"), 15, 0)) /
      2
  );

  const cashFlow = Math.round(
    (score(getRatioVal("Cash Flow", "FCF Margin (%)"), 15, 0) +
      score(getRatioVal("Cash Flow", "Operating CF Margin (%)"), 15, 0)) /
      2
  );

  const total = Math.round(
    profitability * 0.3 + liquidity * 0.15 + solvency * 0.2 + growth * 0.2 + cashFlow * 0.15
  );

  return { total, profitability, liquidity, solvency, growth, cashFlow };
}

// ─── formatting ───────────────────────────────────────────────────────────────

export function fmtCr(v: number | null, decimals = 0): string {
  if (v === null || isNaN(v)) return "—";
  if (Math.abs(v) >= 100000)
    return `₹${(v / 100000).toLocaleString("en-IN", { maximumFractionDigits: 2 })}L Cr`;
  if (Math.abs(v) >= 1000)
    return `₹${(v / 1000).toLocaleString("en-IN", { maximumFractionDigits: decimals > 0 ? decimals : 1 })}K Cr`;
  return `₹${v.toLocaleString("en-IN", { maximumFractionDigits: decimals })} Cr`;
}

export function fmtNum(v: number | null, suffix = "", decimals = 2): string {
  if (v === null || isNaN(v)) return "—";
  return `${v.toLocaleString("en-IN", { maximumFractionDigits: decimals })}${suffix}`;
}

export function fmtRaw(v: number | null, format: SnapshotKPI["format"]): string {
  if (v === null) return "—";
  switch (format) {
    case "crore":  return fmtCr(v);
    case "percent":return `${fmtNum(v, "%", 1)}`;
    case "ratio":  return fmtNum(v, "x");
    case "rs":     return `₹${fmtNum(v, "", 2)}`;
    default:       return String(v);
  }
}
