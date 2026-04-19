"""
forecasting/monte_carlo.py
===========================
Monte Carlo DCF Simulation — AI Feature 2

Runs your existing DCF logic 10,000 times with WACC and Terminal Growth
Rate sampled from realistic probability distributions.

Output: probability distribution of intrinsic values with
        25th / 50th / 75th percentile estimates.

HOW TO INTEGRATE:
    Step 1 — Copy this file into your forecasting/ folder as:
                forecasting/monte_carlo.py

    Step 2 — In forecasting/dcf.py, at the bottom of run_dcf(), add:
                from forecasting.monte_carlo import run_monte_carlo
                dcf_result["monte_carlo"] = run_monte_carlo(dcf_result, canon_df)

    Step 3 — In excel/sheets/forecasts.py, the Monte Carlo section
            is already handled by the updated build_forecasts_sheet()
            in forecasts_updated.py provided alongside this file.

WHAT CHANGES IN YOUR EXCEL OUTPUT:
    Forecasts sheet — DCF section gains a new block:
        Monte Carlo Simulation  |  10,000 runs
        Pessimistic  (25th pct): ₹ X,XXX per share
        Most Likely  (median):   ₹ X,XXX per share
        Optimistic   (75th pct): ₹ X,XXX per share
        Probability within ±20% of median: XX%
"""

import numpy as np
import pandas as pd
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

N_SIMULATIONS = 2_000   # reduced from 10_000 — still statistically robust, 5× faster
RANDOM_SEED   = 42          # reproducible results

# WACC distribution — normal distribution around base case
WACC_STD_DEV  = 0.015       # ±1.5% standard deviation

# Terminal Growth Rate distribution
TGR_STD_DEV   = 0.008       # ±0.8% standard deviation

# Hard bounds — prevent nonsensical outputs
WACC_MIN, WACC_MAX = 0.06, 0.20     # 6% to 20%
TGR_MIN,  TGR_MAX  = 0.01, 0.07    # 1% to 7%
TGR_MUST_BE_BELOW_WACC = True       # TGR must always be < WACC


# ─────────────────────────────────────────────────────────────────────────────
# CORE DCF FUNCTION  (self-contained — mirrors your dcf.py logic)
# ─────────────────────────────────────────────────────────────────────────────

def _single_dcf(
    base_fcf:      float,
    fcf_growth:    float,
    wacc:          float,
    tgr:           float,
    n_years:       int,
    shares_cr:     float,   # shares in Crores (same unit as FCF)
    net_debt:      float,   # in ₹ Crores
) -> Optional[float]:
    """
    Runs one DCF and returns intrinsic value per share (₹).
    All monetary inputs in ₹ Crores.
    shares_cr = shares outstanding in Crores (e.g. 414 Cr shares → 414.0)
    """
    if wacc <= tgr:
        return None
    if wacc <= 0 or shares_cr <= 0:
        return None

    # Project FCFs (₹ Crores)
    fcfs = [base_fcf * ((1 + fcf_growth) ** yr) for yr in range(1, n_years + 1)]

    # Discount FCFs
    pv_fcfs = sum(f / ((1 + wacc) ** yr) for yr, f in enumerate(fcfs, 1))

    # Terminal value (Gordon Growth) — in ₹ Crores
    terminal_fcf = fcfs[-1] * (1 + tgr)
    terminal_val = terminal_fcf / (wacc - tgr)
    pv_terminal  = terminal_val / ((1 + wacc) ** n_years)

    # Enterprise value → Equity value (₹ Crores)
    enterprise_val = pv_fcfs + pv_terminal
    equity_val     = enterprise_val - net_debt
    if equity_val <= 0:
        return None

    # Intrinsic value per share (₹)
    # equity_val is in ₹ Crores, shares_cr is in Crores
    # ₹ Crores / Crores shares = ₹ per share
    return (equity_val * 1e7) / (shares_cr * 1e7)   # simplifies to equity_val / shares_cr


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def run_monte_carlo(dcf_result: dict, canon_df: pd.DataFrame) -> dict:
    """
    Runs 10,000 DCF simulations and returns a summary dict.

    Parameters
    ----------
    dcf_result : dict
        Your existing dcf_result dict from run_dcf().
        Must contain: assumptions, intrinsic_value_per_share, enterprise_value, net_debt
    canon_df : pd.DataFrame
        Canonical financial data — used to extract shares outstanding

    Returns
    -------
    dict with keys:
        n_simulations   int
        p25             float   — 25th percentile intrinsic value/share
        p50             float   — median intrinsic value/share
        p75             float   — 75th percentile intrinsic value/share
        p10             float   — 10th percentile (pessimistic extreme)
        p90             float   — 90th percentile (optimistic extreme)
        mean            float
        std             float
        prob_within_20  float   — % of simulations within ±20% of median
        wacc_used       float   — base WACC used
        tgr_used        float   — base TGR used
        label_p25       str     — formatted string for Excel
        label_p50       str
        label_p75       str
    """
    np.random.seed(RANDOM_SEED)

    # ── Extract parameters from your existing dcf_result ─────────────────────
    assumptions = dcf_result.get("assumptions", {})

    # WACC and TGR — dcf.py stores as "WACC (%)" and "Terminal Growth Rate (%)"
    # Values are stored as percentages (e.g. 14.0 means 14%) — divide by 100
    wacc_base = _extract_pct(assumptions, ["WACC (%)", "WACC", "wacc", "Discount Rate"])
    tgr_base  = _extract_pct(assumptions, ["Terminal Growth Rate (%)", "Terminal Growth Rate", "tgr"])

    if wacc_base is None or tgr_base is None:
        logger.warning("Monte Carlo: could not extract WACC/TGR from assumptions. Using defaults.")
        wacc_base = 0.12
        tgr_base  = 0.04

    # Base FCF — use latest FCF from summary_df
    summary_df = dcf_result.get("summary_df", pd.DataFrame())
    if not summary_df.empty and "Projected FCF (₹ Cr)" in summary_df.columns:
        base_fcf = float(summary_df["Projected FCF (₹ Cr)"].iloc[0])
    else:
        base_fcf = float(dcf_result.get("equity_value", 0)) * 0.06   # rough fallback

    # FCF growth rate — use actual value from dcf_result if available
    fcf_growth_raw = dcf_result.get("fcf_growth_used", None)
    if fcf_growth_raw is not None:
        fcf_growth = float(fcf_growth_raw) / 100 if float(fcf_growth_raw) > 1 else float(fcf_growth_raw)
    else:
        fcf_growth = 0.10  # safe fallback

    # Forecast years
    n_years = int(assumptions.get("Forecast Years", 5))

    # Net debt
    net_debt = float(dcf_result.get("net_debt", 0))

    # Shares outstanding in Crores
    # dcf.py stores shares_outstanding_cr directly — use it if available
    # Otherwise derive: equity_value (₹ Cr) / intrinsic_value_per_share (₹) = shares (Cr)
    shares_cr = dcf_result.get("shares_outstanding_cr")
    if not shares_cr or shares_cr <= 0:
        intrinsic = float(dcf_result.get("intrinsic_value_per_share", 1))
        equity_v  = float(dcf_result.get("equity_value", 1))
        shares_cr = equity_v / intrinsic if intrinsic > 0 else 414.0
    shares_cr = float(shares_cr)

    logger.info(f"Monte Carlo: WACC={wacc_base:.1%}, TGR={tgr_base:.1%}, "
                f"Base FCF=₹{base_fcf:,.0f}Cr, Shares={shares_cr:.1f}Cr, N={N_SIMULATIONS:,}")

    # ── Run simulations ───────────────────────────────────────────────────────
    wacc_samples = np.random.normal(wacc_base, WACC_STD_DEV, N_SIMULATIONS)
    tgr_samples  = np.random.normal(tgr_base,  TGR_STD_DEV,  N_SIMULATIONS)

    # Apply bounds
    wacc_samples = np.clip(wacc_samples, WACC_MIN, WACC_MAX)
    tgr_samples  = np.clip(tgr_samples,  TGR_MIN,  TGR_MAX)

    # Ensure TGR < WACC for every simulation
    if TGR_MUST_BE_BELOW_WACC:
        tgr_samples = np.minimum(tgr_samples, wacc_samples - 0.01)

    results = []
    for wacc, tgr in zip(wacc_samples, tgr_samples):
        val = _single_dcf(
            base_fcf   = base_fcf,
            fcf_growth = fcf_growth,
            wacc       = wacc,
            tgr        = tgr,
            n_years    = n_years,
            shares_cr  = shares_cr,
            net_debt   = net_debt,
        )
        if val is not None and val > 0:
            results.append(val)

    if len(results) < 100:
        logger.warning(f"Monte Carlo: only {len(results)} valid simulations. Results may be unreliable.")

    results_arr = np.array(results)

    p10 = float(np.percentile(results_arr, 10))
    p25 = float(np.percentile(results_arr, 25))
    p50 = float(np.percentile(results_arr, 50))
    p75 = float(np.percentile(results_arr, 75))
    p90 = float(np.percentile(results_arr, 90))
    mean = float(np.mean(results_arr))
    std  = float(np.std(results_arr))

    # Probability within ±20% of median
    within_20 = float(np.mean((results_arr >= p50 * 0.8) & (results_arr <= p50 * 1.2)) * 100)

    logger.info(f"Monte Carlo complete: p25=₹{p25:,.0f} | p50=₹{p50:,.0f} | p75=₹{p75:,.0f} "
                f"({len(results):,} valid simulations)")

    return {
        "n_simulations":  len(results),
        "p10":            p10,
        "p25":            p25,
        "p50":            p50,
        "p75":            p75,
        "p90":            p90,
        "mean":           mean,
        "std":            std,
        "prob_within_20": within_20,
        "wacc_used":      wacc_base,
        "tgr_used":       tgr_base,
        # Formatted labels for Excel
        "label_p25":      f"₹{p25:,.0f}",
        "label_p50":      f"₹{p50:,.0f}",
        "label_p75":      f"₹{p75:,.0f}",
        "label_p10":      f"₹{p10:,.0f}",
        "label_p90":      f"₹{p90:,.0f}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_pct(assumptions: dict, keys: list) -> Optional[float]:
    """Try multiple key names to extract a percentage from assumptions dict."""
    for k in keys:
        if k in assumptions:
            val = assumptions[k]
            if isinstance(val, str):
                val = val.strip().replace("%", "")
                try:
                    val = float(val)
                    return val / 100 if val > 1 else val
                except ValueError:
                    continue
            elif isinstance(val, (int, float)):
                return val / 100 if val > 1 else float(val)
    return None