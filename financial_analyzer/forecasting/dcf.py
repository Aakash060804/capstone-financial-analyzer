"""
Discounted Cash Flow valuation.
Projects FCF for DCF_PROJECTION_YEARS, applies terminal value,
discounts at WACC to get intrinsic equity value per share.
"""

import pandas as pd
import numpy as np
from config.settings import (
    DCF_WACC, DCF_TERMINAL_GROWTH, DCF_PROJECTION_YEARS
)
from utils.logger import get_logger

logger = get_logger(__name__)


def run_dcf(canon: pd.DataFrame, face_value: int = 10, wacc: float = None) -> dict:
    """
    Returns a dict with all DCF components.

    Parameters
    ----------
    canon      : canonical DataFrame from build_canonical()
    face_value : face value per share in Rs — extracted from Screener
                Common values: 1 (Infosys/TCS/Wipro), 2 (HDFC), 5 (Maruti), 10 (PSUs)
                Defaults to 10 if not provided (most conservative fallback)
    """
    def last(key):
        if key not in canon.index:
            return np.nan
        mar_cols = [c for c in canon.columns if "Mar" in str(c)]
        vals = canon.loc[key, mar_cols].dropna()
        return float(vals.iloc[-1]) if len(vals) else np.nan

    def last_yr():
        mar_cols = [c for c in canon.columns if "Mar" in str(c)]
        return mar_cols[-1] if mar_cols else "Mar 2024"

    # ── Inputs ────────────────────────────────────────────────────────────────
    base_cfo    = last("cfo")
    base_capex  = abs(last("capex"))
    base_fcf    = base_cfo - base_capex
    net_debt    = last("total_borrowings") - last("cash")
    equity_val  = last("total_equity")

    # Shares outstanding: equity_capital is face value ₹5 or ₹10
    eq_capital  = last("equity_capital")
    # Screener reports equity capital in ₹ Cr, face value typically ₹5
    shares_cr   = eq_capital / 5 * 1e7   # convert to number of shares
    shares_cr   = shares_cr / 1e7        # back to Crores for per-share math

    # Revenue growth as FCF growth proxy (use last 3yr avg revenue growth)
    mar_cols = [c for c in canon.columns if "Mar" in str(c)]
    if "revenue" in canon.index and len(mar_cols) >= 4:
        rev = canon.loc["revenue", mar_cols].dropna()
        cagr = (rev.iloc[-1] / rev.iloc[-4]) ** (1/3) - 1
        fcf_growth = min(cagr, 0.20)   # cap at 20%
    else:
        fcf_growth = 0.10

    wacc            = wacc if wacc is not None else DCF_WACC
    terminal_growth = DCF_TERMINAL_GROWTH
    n_years         = DCF_PROJECTION_YEARS

    logger.info(
        f"DCF inputs — Base FCF: ₹{base_fcf:,.0f} Cr | "
        f"FCF Growth: {fcf_growth*100:.1f}% | "
        f"WACC: {wacc*100:.1f}% | "
        f"Terminal Growth: {terminal_growth*100:.1f}%"
    )

    # ── Project FCF ───────────────────────────────────────────────────────────
    last_label  = last_yr()
    try:
        base_year = int(last_label.replace("Mar ", ""))
    except ValueError:
        base_year = 2024

    projected_fcf = {}
    pv_fcf        = {}
    fcf           = base_fcf

    for i in range(1, n_years + 1):
        yr          = f"Mar {base_year + i}"
        fcf         = fcf * (1 + fcf_growth)
        pv          = fcf / ((1 + wacc) ** i)
        projected_fcf[yr] = round(fcf, 0)
        pv_fcf[yr]        = round(pv,  0)

    # ── Terminal Value ────────────────────────────────────────────────────────
    terminal_fcf    = fcf * (1 + terminal_growth)
    terminal_value  = terminal_fcf / (wacc - terminal_growth)
    pv_terminal     = terminal_value / ((1 + wacc) ** n_years)

    # ── Enterprise and Equity Value ───────────────────────────────────────────
    sum_pv_fcf      = sum(pv_fcf.values())
    enterprise_value= sum_pv_fcf + pv_terminal
    equity_value_dcf= enterprise_value - net_debt

    # Shares outstanding — uses face value extracted from Screener
    # eq_capital is in ₹ Cr, face_value in ₹ → shares in absolute count
    shares_outstanding  = eq_capital * 1e7 / face_value
    intrinsic_per_share = (equity_value_dcf * 1e7) / shares_outstanding

    logger.info(
        f"DCF output — EV: ₹{enterprise_value:,.0f} Cr | "
        f"Equity Value: ₹{equity_value_dcf:,.0f} Cr | "
        f"Face Value: ₹{face_value} | "
        f"Shares: {shares_outstanding/1e7:.1f} Cr | "
        f"Intrinsic/share: ₹{intrinsic_per_share:,.0f}"
    )

    # ── Summary DataFrame ─────────────────────────────────────────────────────
    summary_rows = {}
    for yr in projected_fcf:
        summary_rows[yr] = {
            "Projected FCF (₹ Cr)": projected_fcf[yr],
            "PV of FCF (₹ Cr)":     pv_fcf[yr],
        }
    summary_df = pd.DataFrame(summary_rows).T
    summary_df.index.name = "Year"

    return {
        "projected_fcf":             projected_fcf,
        "pv_fcf":                    pv_fcf,
        "terminal_value":            round(terminal_value, 0),
        "pv_terminal_value":         round(pv_terminal, 0),
        "sum_pv_fcf":                round(sum_pv_fcf, 0),
        "enterprise_value":          round(enterprise_value, 0),
        "net_debt":                  round(net_debt, 0),
        "equity_value":              round(equity_value_dcf, 0),
        "shares_outstanding_cr":     round(eq_capital / face_value, 2),
        "intrinsic_value_per_share": round(intrinsic_per_share, 0),
        "fcf_growth_used":           round(fcf_growth * 100, 2),
        "wacc":                      wacc * 100,
        "terminal_growth":           terminal_growth * 100,
        "assumptions": {
            "Base FCF (₹ Cr)":          round(base_fcf, 0),
            "FCF Growth Rate (%)":      round(fcf_growth * 100, 2),
            "WACC (%)":                 wacc * 100,
            "Terminal Growth Rate (%)": terminal_growth * 100,
            "Projection Years":         n_years,
            "Net Debt (₹ Cr)":          round(net_debt, 0),
            "Face Value (₹)":           face_value,
        },
        "summary_df": summary_df,
    }