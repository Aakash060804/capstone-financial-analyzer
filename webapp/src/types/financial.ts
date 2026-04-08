// ─────────────────────────────────────────────────────────────────────────────
// Shared table shape produced by json_exporter.py _df_to_table()
// ─────────────────────────────────────────────────────────────────────────────
export interface DataTable {
  headers: string[];           // ["metric", "Mar 2020", "Mar 2021", ...]
  rows: Record<string, string | number | null>[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Meta
// ─────────────────────────────────────────────────────────────────────────────
export interface Meta {
  company_slug: string;
  company_name: string;
  face_value_inr: number;
  generated_at: string;
  source: string;
  currency: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Statements (Sheet 1)
// ─────────────────────────────────────────────────────────────────────────────
export interface Statements {
  income_statement: DataTable;
  balance_sheet: DataTable;
  cash_flow: DataTable;
}

// ─────────────────────────────────────────────────────────────────────────────
// Ratios (Sheet 2)
// ─────────────────────────────────────────────────────────────────────────────
export type Ratios = Record<string, DataTable>;

// ─────────────────────────────────────────────────────────────────────────────
// DuPont (Sheet 3)
// ─────────────────────────────────────────────────────────────────────────────
export type DuPont = DataTable;

// ─────────────────────────────────────────────────────────────────────────────
// Common Size (Sheet 4)
// ─────────────────────────────────────────────────────────────────────────────
export interface CommonSize {
  income_statement: DataTable;
  balance_sheet: DataTable;
}

// ─────────────────────────────────────────────────────────────────────────────
// Schedules (Sheets 5 & 6)
// ─────────────────────────────────────────────────────────────────────────────
export interface Schedules {
  working_capital: DataTable;
  debt: DataTable;
}

// ─────────────────────────────────────────────────────────────────────────────
// Forecasts (Sheets 7 & 8)
// ─────────────────────────────────────────────────────────────────────────────
export interface DCFValuation {
  enterprise_value_cr: number | null;
  net_debt_cr: number | null;
  equity_value_cr: number | null;
  shares_outstanding_cr: number | null;
  intrinsic_value_per_share: number | null;
  sum_pv_fcf_cr: number | null;
  pv_terminal_value_cr: number | null;
  terminal_value_cr: number | null;
}

export interface MonteCarlo {
  n_simulations: number;
  p10: number; p25: number; p50: number; p75: number; p90: number;
  mean: number; std: number;
  prob_within_20: number;
  label_p10: string; label_p25: string; label_p50: string;
  label_p75: string; label_p90: string;
}

export interface SensitivityTable {
  row_label: string;
  col_label: string;
  row_values: string[];
  col_values: string[];
  table: DataTable;
}

export interface WaccResult {
  wacc: number | null;
  cost_of_equity: number | null;
  cost_of_debt: number | null;
  beta: number | null;
  beta_source: string;
  debt_weight: number | null;
  equity_weight: number | null;
  risk_free_rate: number | null;
  equity_risk_premium: number | null;
  tax_rate: number | null;
  computation_log: string[];
}

export interface DCF {
  projections: DataTable;
  valuation: DCFValuation;
  assumptions: Record<string, number | string | null>;
  projected_fcf: Record<string, number | null>;
  pv_fcf: Record<string, number | null>;
  wacc_used: number | null;
  terminal_growth_used: number | null;
  fcf_growth_used: number | null;
  monte_carlo: MonteCarlo;
}

export interface Forecasts {
  scenarios: Record<string, DataTable>;
  dcf: DCF;
  sensitivity: SensitivityTable;
  wacc: WaccResult;
  prophet: { available: boolean; models?: Record<string, { mape: number; forecast: DataTable }> };
}

// ─────────────────────────────────────────────────────────────────────────────
// AI Commentary (Sheet 9)
// ─────────────────────────────────────────────────────────────────────────────
export interface CategoryCommentary {
  category: string;
  headline: string;
  commentary: string;
  trend: "improving" | "stable" | "deteriorating" | string;
}

export interface InvestmentThesis {
  overall_rating: string;
  key_strengths: string[];
  key_concerns: string[];
  executive_summary: string;
}

export interface RedFlag {
  metric: string;
  value: string;
  severity: "high" | "medium" | "low" | string;
  explanation: string;
}

export interface RedFlagReport {
  total_flags: number;
  overall_risk: string;
  risk_summary: string;
  flags: RedFlag[];
}

export interface AICommentary {
  company: string;
  categories: CategoryCommentary[];
  thesis: InvestmentThesis;
  red_flags: RedFlagReport;
}

// ─────────────────────────────────────────────────────────────────────────────
// Audit
// ─────────────────────────────────────────────────────────────────────────────
export interface AnomalyFlag {
  severity: string; method: string;
  metric: string;   year: string;
  value: number | null; reason: string;
}

export interface Audit {
  data_shape: { canonical_rows: number; canonical_cols: number; ratio_rows: number; ratio_cols: number };
  anomaly_detection: {
    summary: Record<string, number | string>;
    flags: AnomalyFlag[];
  };
  industry_classification: {
    sector: string;
    confidence: number;
    peers: string[];
    peer_medians: Record<string, number>;
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Root payload
// ─────────────────────────────────────────────────────────────────────────────
export interface FinancialData {
  meta: Meta;
  statements: Statements;
  ratios: Ratios;
  dupont: DuPont;
  common_size: CommonSize;
  schedules: Schedules;
  forecasts: Forecasts;
  ai_commentary: AICommentary;
  audit: Audit;
}
