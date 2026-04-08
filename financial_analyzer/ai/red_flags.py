"""
Rule-based red flag scanner.
Runs independently of LLM — always produces output.
LLM red flag chain adds qualitative context on top of this.
"""

import pandas as pd
import numpy as np
from config.settings import RED_FLAG_THRESHOLDS
from utils.logger    import get_logger

logger = get_logger(__name__)


def scan_red_flags(ratio_df: pd.DataFrame, company: str) -> list[dict]:
    """
    Scans ratio DataFrame against thresholds and trend rules.
    Returns list of flag dicts with metric, value, severity, explanation.
    """
    flags = []

    # Get most recent Mar year
    mar_cols = [c for c in ratio_df.columns if "Mar" in str(c)]
    if not mar_cols:
        return flags

    latest_yr  = mar_cols[-1]
    prev_yr    = mar_cols[-2] if len(mar_cols) >= 2 else None
    prev2_yr   = mar_cols[-3] if len(mar_cols) >= 3 else None

    def get(metric, yr):
        if metric in ratio_df.index and yr in ratio_df.columns:
            v = ratio_df.loc[metric, yr]
            return float(v) if not pd.isna(v) else None
        return None

    def add_flag(metric, value, severity, explanation):
        flags.append({
            "metric":      metric,
            "value":       str(round(value, 2)) if isinstance(value, float) else str(value),
            "severity":    severity,
            "explanation": explanation,
        })
        logger.debug(f"  Red flag [{severity}]: {metric} = {value} — {explanation}")

    # ── Threshold checks ──────────────────────────────────────────────────────

    cr = get("Current Ratio (x)", latest_yr)
    if cr is not None and cr < RED_FLAG_THRESHOLDS["current_ratio_min"]:
        add_flag("Current Ratio (x)", cr, "high",
                f"Current ratio of {cr:.2f}x is below the minimum threshold of "
                f"{RED_FLAG_THRESHOLDS['current_ratio_min']}x, indicating potential short-term liquidity stress.")

    qr = get("Quick Ratio (x)", latest_yr)
    if qr is not None and qr < RED_FLAG_THRESHOLDS["quick_ratio_min"]:
        add_flag("Quick Ratio (x)", qr, "medium",
                f"Quick ratio of {qr:.2f}x is below {RED_FLAG_THRESHOLDS['quick_ratio_min']}x.")

    ic = get("Interest Coverage (x)", latest_yr)
    if ic is not None and ic < RED_FLAG_THRESHOLDS["interest_coverage_min"]:
        add_flag("Interest Coverage (x)", ic, "high",
                f"Interest coverage of {ic:.1f}x is below the safe threshold of "
                f"{RED_FLAG_THRESHOLDS['interest_coverage_min']}x.")

    de = get("Debt-to-Equity (x)", latest_yr)
    if de is not None and de > RED_FLAG_THRESHOLDS["debt_equity_max"]:
        add_flag("Debt-to-Equity (x)", de, "high",
                f"D/E ratio of {de:.2f}x exceeds maximum threshold of "
                f"{RED_FLAG_THRESHOLDS['debt_equity_max']}x.")

    fcfm = get("FCF Margin (%)", latest_yr)
    if fcfm is not None and fcfm < RED_FLAG_THRESHOLDS["fcf_margin_min"]:
        add_flag("FCF Margin (%)", fcfm, "medium",
                f"Negative FCF margin of {fcfm:.1f}% indicates the company is "
                f"consuming more cash than it generates from operations after capex.")

    roce = get("Return on Capital Employed % (ROCE)", latest_yr)
    if roce is not None and roce < RED_FLAG_THRESHOLDS["roce_min"]:
        add_flag("Return on Capital Employed % (ROCE)", roce, "medium",
                f"ROCE of {roce:.1f}% is below the minimum acceptable threshold of "
                f"{RED_FLAG_THRESHOLDS['roce_min']}%, suggesting poor capital deployment.")

    # ── Trend deterioration checks ────────────────────────────────────────────

    if prev_yr and prev2_yr:
        for metric in ["EBITDA Margin (%)", "Net Profit Margin (%)", "Return on Equity % (ROE)"]:
            v0 = get(metric, prev2_yr)
            v1 = get(metric, prev_yr)
            v2 = get(metric, latest_yr)
            if all(v is not None for v in [v0, v1, v2]):
                if v2 < v1 < v0:
                    add_flag(metric, v2, "medium",
                            f"{metric} has declined consistently over 3 years: "
                            f"{v0:.1f}% → {v1:.1f}% → {v2:.1f}%.")

    # ── Negative FCF trend check ───────────────────────────────────────────────
    if prev_yr and prev2_yr:
        fcf_vals = [get("Free Cash Flow (₹ Cr)", yr) for yr in [prev2_yr, prev_yr, latest_yr]]
        if all(v is not None for v in fcf_vals) and all(v < 0 for v in fcf_vals):
            add_flag("Free Cash Flow (₹ Cr)", fcf_vals[-1], "high",
                    f"FCF has been negative for 3 consecutive years: "
                    f"{fcf_vals[0]:,.0f} → {fcf_vals[1]:,.0f} → {fcf_vals[2]:,.0f} ₹ Cr.")

    logger.info(f"Rule-based scan complete: {len(flags)} flags for {company}")
    return flags