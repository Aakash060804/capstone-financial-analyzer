"""
ai/context_builder.py
======================
Computes 3 layers of context for every ratio BEFORE sending to Claude.

    Layer 1 — 5-year historical average  (company's own baseline)
    Layer 2 — Trend direction            (improving / stable / deteriorating)
    Layer 3 — Peer median                (IT sector benchmarks)

Called from chains.py — see _build_context_block() below.
"""

import numpy as np
import pandas as pd
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# PEER MEDIANS  —  approximate medians for Indian listed companies by sector
# ─────────────────────────────────────────────────────────────────────────────

PEER_MEDIANS = {
    "IT": {
        "EBITDA Margin (%)":                   0.258,
        "EBIT Margin (%)":                     0.228,
        "Net Profit Margin (%)":               0.178,
        "Return on Assets % (ROA)":            0.182,
        "Return on Equity % (ROE)":            0.312,
        "Return on Capital Employed % (ROCE)": 0.298,
        "Current Ratio (x)":                   1.08,
        "Quick Ratio (x)":                     0.94,
        "Debt-to-Equity (x)":                  0.12,
        "Interest Coverage (x)":               45.0,
        "Operating CF Margin (%)":             0.195,
        "FCF Margin (%)":                      0.123,
        "Asset Turnover (x)":                  1.05,
        "Revenue Growth (%)":                  0.074,
    },
    "AUTO": {
        "EBITDA Margin (%)":                   0.148,
        "Net Profit Margin (%)":               0.082,
        "Return on Equity % (ROE)":            0.178,
        "Return on Capital Employed % (ROCE)": 0.195,
        "Current Ratio (x)":                   0.92,
        "Debt-to-Equity (x)":                  0.18,
        "FCF Margin (%)":                      0.055,
        "Revenue Growth (%)":                  0.088,
    },
    "GENERIC": {
        "EBITDA Margin (%)":                   0.18,
        "Net Profit Margin (%)":               0.10,
        "Return on Equity % (ROE)":            0.15,
        "Return on Capital Employed % (ROCE)": 0.14,
        "Current Ratio (x)":                   1.30,
        "Debt-to-Equity (x)":                  0.60,
        "FCF Margin (%)":                      0.07,
        "Revenue Growth (%)":                  0.10,
    },
}

PCT_METRICS = {
    "EBITDA Margin (%)", "EBIT Margin (%)", "Net Profit Margin (%)",
    "Return on Assets % (ROA)", "Return on Equity % (ROE)",
    "Return on Capital Employed % (ROCE)", "Operating CF Margin (%)",
    "FCF Margin (%)", "Revenue Growth (%)", "CapEx Intensity (%)",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _detect_sector(company: str) -> str:
    name = company.upper()
    if any(k in name for k in ["INFY", "INFOSYS", "TCS", "WIPRO", "HCL", "TECH M"]):
        return "IT"
    if any(k in name for k in ["MARUTI", "TATA MOTORS", "HERO MOTO", "BAJAJ AUTO"]):
        return "AUTO"
    return "GENERIC"


def _five_yr_avg(series: pd.Series) -> Optional[float]:
    """Average of last 5 values excluding the most recent year."""
    clean = series.dropna()
    if len(clean) < 2:
        return None
    baseline = clean.iloc[:-1].tail(5)
    return float(baseline.mean()) if len(baseline) >= 1 else None


def _trend(series: pd.Series, window: int = 3) -> str:
    """Linear regression slope over last `window` values → improving/stable/deteriorating."""
    clean = series.dropna()
    if len(clean) < window:
        return "stable"
    recent = clean.tail(window).values
    slope = np.polyfit(np.arange(len(recent)), recent, 1)[0]
    threshold = 0.02 * abs(np.mean(recent)) if np.mean(recent) != 0 else 0.001
    if slope > threshold:
        return "improving"
    elif slope < -threshold:
        return "deteriorating"
    return "stable"


def _fmt(metric: str, value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    if metric in PCT_METRICS:
        return f"{value * 100:.1f}%"
    if "₹" in metric:
        return f"₹{value:,.0f} Cr"
    if "(x)" in metric or "(days)" in metric:
        return f"{value:.2f}"
    return f"{value:.2f}"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXPORT — called from chains.py
# ─────────────────────────────────────────────────────────────────────────────

def build_context_block(ratio_df: pd.DataFrame, company: str, clustering_result: dict = None) -> str:
    """
    Returns a formatted text block describing historical trends and peer
    comparisons for every ratio.  This block is appended to every Claude prompt.

    Parameters
    ----------
    ratio_df : pd.DataFrame
        Your existing ratio DataFrame (rows = metric names, cols = year labels)
    company : str
        Company name — used to auto-detect sector for peer benchmarks

    Returns
    -------
    str
        Multi-line text block ready to embed in a prompt string
    """
    # Use dynamic clustering result if available, else fallback to keyword detection
    if clustering_result and clustering_result.get("peer_medians"):
        sector = clustering_result.get("sector", _detect_sector(company))
        peers  = clustering_result.get("peer_medians", {})
    else:
        sector = _detect_sector(company)
        peers  = PEER_MEDIANS.get(sector, PEER_MEDIANS["GENERIC"])

    lines = [
        "=" * 68,
        f"CONTEXT BLOCK — Historical Trends & Peer Benchmarks ({sector} sector)",
        "Use this context in every sentence of your commentary.",
        "Do NOT just restate the latest number — reference the trend and peer comparison.",
        "=" * 68,
    ]

    # Only emit rows that have at least one numeric value
    mar_cols = [c for c in ratio_df.columns if "Mar" in str(c)]

    for metric in ratio_df.index:
        series = ratio_df.loc[metric, mar_cols] if mar_cols else ratio_df.loc[metric]
        clean  = series.dropna()
        if len(clean) == 0:
            continue

        latest    = float(clean.iloc[-1])
        avg_5yr   = _five_yr_avg(series)
        trend_dir = _trend(series)
        peer_med  = peers.get(metric)

        # Skip metrics where we have nothing interesting to add
        if avg_5yr is None and peer_med is None:
            continue

        # Build comparison sentence
        parts = [f"{metric}: latest {_fmt(metric, latest)}"]

        if avg_5yr is not None:
            diff_pct = ((latest - avg_5yr) / abs(avg_5yr) * 100) if avg_5yr != 0 else 0
            direction = "above" if diff_pct > 3 else ("below" if diff_pct < -3 else "in-line with")
            parts.append(f"{direction} 5-yr avg {_fmt(metric, avg_5yr)} ({diff_pct:+.1f}%)")

        parts.append(f"trend: {trend_dir}")

        if peer_med is not None:
            vs = "above" if latest > peer_med * 1.05 else ("below" if latest < peer_med * 0.95 else "in-line with")
            parts.append(f"{vs} {sector} peer median {_fmt(metric, peer_med)}")

        lines.append("  • " + " | ".join(parts))

    lines += [
        "=" * 68,
        "INSTRUCTION: Write commentary that cites specific numbers above.",
        "Example: 'EBITDA margin compressed 260bps below its 5-year average",
        "and trails the IT sector peer median — reflecting sustained cost pressure.'",
        "=" * 68,
    ]

    return "\n".join(lines)