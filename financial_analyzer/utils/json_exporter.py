"""
json_exporter.py
────────────────
Converts the full financial analysis pipeline output into a structured JSON
file suitable for serving to a web application.

All 9 Excel sheets are represented:
  1. Financial Statements   (income, balance sheet, cash flow)
  2. Financial Ratios        (6 categories × all years)
  3. DuPont Analysis
  4. Common Size Analysis    (income + balance)
  5. Working Capital Schedule
  6. Debt Schedule
  7. Scenario Forecasts      (base / bull / bear)
  8. DCF Valuation           (projections, sensitivity, Monte Carlo, WACC)
  9. AI Commentary           (categories, thesis, red flags)
  +  Audit / Meta            (anomaly report, clustering, run info)

Usage:
    from utils.json_exporter import export_to_json
    export_to_json(output_dir, company_slug, **all_pipeline_outputs)
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _clean(value: Any) -> Any:
    """Recursively convert non-JSON-serialisable types to native Python types."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 4)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 4)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return str(value)
    if isinstance(value, np.ndarray):
        return _clean(value.tolist())
    return value


def _df_to_table(df: pd.DataFrame | None) -> dict:
    """
    Convert a DataFrame to a web-friendly table dict:
      {
        "headers": ["metric", "Mar 2020", "Mar 2021", ...],
        "rows":    [{"metric": "Revenue", "Mar 2020": 1234.5, ...}, ...]
      }
    The index becomes the "metric" column.
    """
    if df is None or df.empty:
        return {"headers": [], "rows": []}

    df = df.copy()
    df.index = df.index.astype(str)
    df.columns = df.columns.astype(str)

    headers = ["metric"] + list(df.columns)
    rows = []
    for idx, row in df.iterrows():
        entry: dict[str, Any] = {"metric": str(idx)}
        for col in df.columns:
            entry[col] = _clean(row[col])
        rows.append(entry)
    return {"headers": headers, "rows": rows}


def _pydantic_to_dict(obj: Any) -> Any:
    """Safely convert Pydantic model to dict (v1 and v2 compatible)."""
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):        # Pydantic v2
        return _clean(obj.model_dump())
    if hasattr(obj, "dict"):              # Pydantic v1
        return _clean(obj.dict())
    if isinstance(obj, dict):
        return _clean(obj)
    return _clean(str(obj))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION BUILDERS (one per logical sheet)
# ─────────────────────────────────────────────────────────────────────────────

def _build_meta(company_slug: str, company_name: str, face_value: int) -> dict:
    return {
        "company_slug": company_slug.upper(),
        "company_name": company_name,
        "face_value_inr": face_value,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Screener.in (consolidated statements)",
        "currency": "INR Crores",
    }


def _build_statements(stmts: dict) -> dict:
    """Sheet 1 — raw financial statements (income, balance, cash flow)."""
    return {
        "income_statement": _df_to_table(stmts.get("income_statement")),
        "balance_sheet":    _df_to_table(stmts.get("balance_sheet")),
        "cash_flow":        _df_to_table(stmts.get("cash_flow")),
    }


def _build_ratios(ratio_df: pd.DataFrame | None) -> dict:
    """Sheet 2 — financial ratios, split by category."""
    if ratio_df is None or ratio_df.empty:
        return {}

    # Define which ratio belongs to which category
    category_map = {
        "Profitability": [
            "EBITDA Margin (%)", "EBIT Margin (%)", "Net Profit Margin (%)",
            "Return on Assets % (ROA)", "Return on Equity % (ROE)",
            "Return on Capital Employed % (ROCE)",
        ],
        "Utilization": [
            "Asset Turnover (x)", "Fixed Asset Turnover (x)",
            "Inventory Turnover (x)", "Receivables Turnover (x)",
            "Days Inventory Outstanding (days)", "Days Sales Outstanding (days)",
            "Days Payable Outstanding (days)", "Cash Conversion Cycle (days)",
        ],
        "Liquidity": [
            "Current Ratio (x)", "Quick Ratio (x)", "Cash Ratio (x)",
        ],
        "Solvency": [
            "Debt-to-Equity (x)", "Debt-to-Assets (x)",
            "Interest Coverage (x)", "Net Debt (₹ Cr)", "Net Debt / EBITDA (x)",
        ],
        "Cash Flow": [
            "Operating CF Margin (%)", "Free Cash Flow (₹ Cr)",
            "FCF Margin (%)", "FCF to Net Income (x)", "CapEx Intensity (%)",
        ],
        "Growth": [
            "Revenue Growth (%)", "EBITDA Growth (%)", "Net Income Growth (%)",
            "EPS Growth (%)", "CFO Growth (%)",
        ],
    }

    result: dict[str, Any] = {}
    present = set(ratio_df.index.astype(str))

    for category, metrics in category_map.items():
        subset = [m for m in metrics if m in present]
        if subset:
            result[category] = _df_to_table(ratio_df.loc[subset])

    # Capture any ratios not in the category map
    mapped = {m for metrics in category_map.values() for m in metrics}
    uncategorised = [m for m in ratio_df.index.astype(str) if m not in mapped]
    if uncategorised:
        result["Other"] = _df_to_table(ratio_df.loc[uncategorised])

    return result


def _build_dupont(dupont_df: pd.DataFrame | None) -> dict:
    """Sheet 3 — DuPont decomposition."""
    return _df_to_table(dupont_df)


def _build_common_size(
    cs_inc: pd.DataFrame | None,
    cs_bal: pd.DataFrame | None,
) -> dict:
    """Sheet 4 — common size income & balance."""
    return {
        "income_statement": _df_to_table(cs_inc),
        "balance_sheet":    _df_to_table(cs_bal),
    }


def _build_schedules(
    wc_sched: pd.DataFrame | None,
    dt_sched: pd.DataFrame | None,
) -> dict:
    """Sheets 5 & 6 — working capital & debt schedules."""
    return {
        "working_capital": _df_to_table(wc_sched),
        "debt":            _df_to_table(dt_sched),
    }


def _build_forecasts(
    scenarios: dict | None,
    dcf_result: dict | None,
    sensitivity_df: pd.DataFrame | None,
    wacc_result: dict | None,
    prophet_result: dict | None,
) -> dict:
    """Sheet 7 & 8 — scenario forecasts + full DCF valuation."""

    # ── Scenarios ─────────────────────────────────────────────────────────────
    scenarios_out: dict = {}
    if scenarios:
        for name, df in scenarios.items():
            scenarios_out[name] = _df_to_table(df)

    # ── DCF ───────────────────────────────────────────────────────────────────
    dcf_out: dict = {}
    if dcf_result:
        # Projections table
        summary_df = dcf_result.get("summary_df")
        dcf_out["projections"] = _df_to_table(summary_df) if isinstance(summary_df, pd.DataFrame) else {}

        # Valuation summary
        dcf_out["valuation"] = {
            "enterprise_value_cr":      _clean(dcf_result.get("enterprise_value")),
            "net_debt_cr":              _clean(dcf_result.get("net_debt")),
            "equity_value_cr":          _clean(dcf_result.get("equity_value")),
            "shares_outstanding_cr":    _clean(dcf_result.get("shares_outstanding_cr")),
            "intrinsic_value_per_share": _clean(dcf_result.get("intrinsic_value_per_share")),
            "sum_pv_fcf_cr":            _clean(dcf_result.get("sum_pv_fcf")),
            "pv_terminal_value_cr":     _clean(dcf_result.get("pv_terminal_value")),
            "terminal_value_cr":        _clean(dcf_result.get("terminal_value")),
        }

        # Assumptions
        dcf_out["assumptions"] = _clean(dcf_result.get("assumptions", {}))

        # Projected FCF & PV year-by-year
        dcf_out["projected_fcf"] = _clean(dcf_result.get("projected_fcf", {}))
        dcf_out["pv_fcf"]        = _clean(dcf_result.get("pv_fcf", {}))

        # WACC used
        dcf_out["wacc_used"]           = _clean(dcf_result.get("wacc"))
        dcf_out["terminal_growth_used"] = _clean(dcf_result.get("terminal_growth"))
        dcf_out["fcf_growth_used"]      = _clean(dcf_result.get("fcf_growth_used"))

        # Monte Carlo
        mc = dcf_result.get("monte_carlo", {})
        dcf_out["monte_carlo"] = _clean(mc) if mc else {}

    # ── Sensitivity ────────────────────────────────────────────────────────────
    sensitivity_out: dict = {}
    if sensitivity_df is not None and not sensitivity_df.empty:
        df = sensitivity_df.copy()
        df.index   = df.index.astype(str)
        df.columns = df.columns.astype(str)

        sensitivity_out = {
            "row_label":    str(df.index.name or "WACC"),
            "col_label":    str(df.columns.name or "Terminal Growth Rate"),
            "row_values":   list(df.index),
            "col_values":   list(df.columns),
            "table":        _df_to_table(df),
        }

    # ── WACC breakdown ────────────────────────────────────────────────────────
    wacc_out: dict = {}
    if wacc_result:
        wacc_out = {
            "wacc":               _clean(wacc_result.get("wacc")),
            "cost_of_equity":     _clean(wacc_result.get("cost_of_equity")),
            "cost_of_debt":       _clean(wacc_result.get("cost_of_debt")),
            "beta":               _clean(wacc_result.get("beta")),
            "beta_source":        wacc_result.get("beta_source"),
            "debt_weight":        _clean(wacc_result.get("debt_weight")),
            "equity_weight":      _clean(wacc_result.get("equity_weight")),
            "risk_free_rate":     _clean(wacc_result.get("risk_free_rate")),
            "equity_risk_premium": _clean(wacc_result.get("equity_risk_premium")),
            "tax_rate":           _clean(wacc_result.get("tax_rate")),
            "computation_log":    wacc_result.get("computation_log", []),
        }

    # ── Prophet ───────────────────────────────────────────────────────────────
    prophet_out: dict = {"available": False}
    if prophet_result and prophet_result.get("available"):
        prophet_out["available"] = True
        prophet_out["models"] = {}
        for metric, model_data in prophet_result.get("models", {}).items():
            forecast_df = model_data.get("forecast")
            if isinstance(forecast_df, pd.DataFrame):
                prophet_out["models"][metric] = {
                    "mape": _clean(model_data.get("mape")),
                    "forecast": _df_to_table(forecast_df),
                }

    return {
        "scenarios":   scenarios_out,
        "dcf":         dcf_out,
        "sensitivity": sensitivity_out,
        "wacc":        wacc_out,
        "prophet":     prophet_out,
    }


def _build_ai_commentary(report: Any) -> dict:
    """Sheet 9 — AI-generated narrative commentary."""
    if report is None:
        return {}

    data = _pydantic_to_dict(report)

    # Normalise to expected shape regardless of Pydantic version
    out: dict[str, Any] = {
        "company": data.get("company", ""),
    }

    # Categories
    categories = data.get("categories", [])
    out["categories"] = [
        {
            "category":    c.get("category", ""),
            "headline":    c.get("headline", ""),
            "commentary":  c.get("commentary", ""),
            "trend":       c.get("trend", ""),
        }
        for c in categories
    ]

    # Investment thesis
    thesis = data.get("thesis", {})
    out["thesis"] = {
        "overall_rating":    thesis.get("overall_rating", ""),
        "key_strengths":     thesis.get("key_strengths", []),
        "key_concerns":      thesis.get("key_concerns", []),
        "executive_summary": thesis.get("executive_summary", ""),
    }

    # Red flags
    red_flags = data.get("red_flags", {})
    out["red_flags"] = {
        "total_flags":   red_flags.get("total_flags", 0),
        "overall_risk":  red_flags.get("overall_risk", ""),
        "risk_summary":  red_flags.get("risk_summary", ""),
        "flags": [
            {
                "metric":      f.get("metric", ""),
                "value":       f.get("value", ""),
                "severity":    f.get("severity", ""),
                "explanation": f.get("explanation", ""),
            }
            for f in red_flags.get("flags", [])
        ],
    }

    return out


def _build_audit(
    anomaly_report: dict | None,
    clustering_result: dict | None,
    canon_shape: tuple,
    ratio_shape: tuple,
) -> dict:
    """Audit trail — data quality, anomaly scan, industry classification."""

    anomaly_out: dict = {}
    if anomaly_report:
        anomaly_out = {
            "summary": _clean(anomaly_report.get("summary", {})),
            "flags": [
                {
                    "severity": f.get("severity", ""),
                    "method":   f.get("method", ""),
                    "metric":   f.get("metric", ""),
                    "year":     str(f.get("year", "")),
                    "value":    _clean(f.get("value")),
                    "reason":   f.get("reason", ""),
                }
                for f in anomaly_report.get("flags", [])
            ],
        }

    clustering_out: dict = {}
    if clustering_result:
        clustering_out = {
            "sector":      clustering_result.get("sector", ""),
            "confidence":  _clean(clustering_result.get("confidence")),
            "peers":       clustering_result.get("peers", []),
            "peer_medians": _clean(clustering_result.get("peer_medians", {})),
        }

    return {
        "data_shape": {
            "canonical_rows": canon_shape[0] if canon_shape else 0,
            "canonical_cols": canon_shape[1] if len(canon_shape) > 1 else 0,
            "ratio_rows":     ratio_shape[0] if ratio_shape else 0,
            "ratio_cols":     ratio_shape[1] if len(ratio_shape) > 1 else 0,
        },
        "anomaly_detection":       anomaly_out,
        "industry_classification": clustering_out,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def export_to_json(
    output_dir: str,
    company_slug: str,
    company_name: str,
    statements: dict,
    canon_df: "pd.DataFrame",
    ratio_df: "pd.DataFrame",
    dupont_df: "pd.DataFrame",
    cs_inc: "pd.DataFrame",
    cs_bal: "pd.DataFrame",
    wc_schedule: "pd.DataFrame",
    debt_schedule: "pd.DataFrame",
    report: Any,
    scenarios: dict,
    dcf_result: dict,
    sensitivity_df: "pd.DataFrame",
    anomaly_report: dict,
    wacc_result: dict | None,
    prophet_result: dict | None,
    clustering_result: dict | None,
) -> str:
    """
    Build the complete JSON payload and write it to:
        {output_dir}/{company_slug}_financial_data.json

    Returns the absolute path to the written file.
    """
    face_value = statements.get("_face_value", 10)

    payload = {
        "meta":             _build_meta(company_slug, company_name, face_value),
        "statements":       _build_statements(statements),
        "ratios":           _build_ratios(ratio_df),
        "dupont":           _build_dupont(dupont_df),
        "common_size":      _build_common_size(cs_inc, cs_bal),
        "schedules":        _build_schedules(wc_schedule, debt_schedule),
        "forecasts":        _build_forecasts(
                                scenarios,
                                dcf_result,
                                sensitivity_df,
                                wacc_result,
                                prophet_result,
                            ),
        "ai_commentary":    _build_ai_commentary(report),
        "audit":            _build_audit(
                                anomaly_report,
                                clustering_result,
                                canon_df.shape if canon_df is not None else (),
                                ratio_df.shape  if ratio_df  is not None else (),
                            ),
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{company_slug.upper()}_financial_data.json")

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)

    return out_path
