"""
Computes 25+ financial ratios from the canonical DataFrame.
All inputs come from canon: pd.DataFrame (index=metric, columns=years).
All outputs are pd.Series keyed by year.
"""

import pandas as pd
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)


def _safe_div(num: pd.Series, denom: pd.Series) -> pd.Series:
    """Division safe against zeros and NaN."""
    return num.div(denom.replace(0, np.nan))


def _row(canon: pd.DataFrame, key: str) -> pd.Series:
    """Fetch a row safely. Returns NaN series if key missing."""
    if key in canon.index:
        return canon.loc[key].astype(float)
    logger.debug(f"Metric '{key}' not found in canonical DataFrame")
    return pd.Series(np.nan, index=canon.columns)


def _avg(series: pd.Series) -> pd.Series:
    """Rolling 2-period average — used for turnover ratios."""
    return (series + series.shift(1)) / 2


def compute_all(canon: pd.DataFrame) -> pd.DataFrame:
    """
    Master function. Computes all ratio categories and returns
    a single DataFrame: index=ratio_name, columns=years.
    """
    profitability   = compute_profitability(canon)
    utilization     = compute_utilization(canon)
    liquidity       = compute_liquidity(canon)
    solvency        = compute_solvency(canon)
    cashflow        = compute_cashflow(canon)
    growth          = compute_growth(canon)

    all_ratios = {
        **profitability,
        **utilization,
        **liquidity,
        **solvency,
        **cashflow,
        **growth,
    }

    df = pd.DataFrame(all_ratios).T
    df.index.name  = "Ratio"
    df.columns     = canon.columns

    logger.info(f"Ratios computed: {len(all_ratios)} ratios × {df.shape[1]} years")
    return df


# ─── Category functions ───────────────────────────────────────────────────────

def compute_profitability(canon: pd.DataFrame) -> dict[str, pd.Series]:
    rev    = _row(canon, "revenue")
    ebitda = _row(canon, "ebitda")
    ebit   = _row(canon, "ebit")
    ni     = _row(canon, "net_income")
    ta     = _row(canon, "total_assets")
    eq     = _row(canon, "total_equity")
    cl     = _row(canon, "total_current_liab")

    ta_avg = _avg(ta)
    eq_avg = _avg(eq)

    # Capital employed = Total Assets - Current Liabilities
    ce     = ta - cl
    ce_avg = _avg(ce)

    return {
        "EBITDA Margin (%)":                    _safe_div(ebitda, rev) * 100,
        "EBIT Margin (%)":                      _safe_div(ebit, rev) * 100,
        "Net Profit Margin (%)":                _safe_div(ni, rev) * 100,
        "Return on Assets % (ROA)":             _safe_div(ni, ta_avg) * 100,
        "Return on Equity % (ROE)":             _safe_div(ni, eq_avg) * 100,
        "Return on Capital Employed % (ROCE)":  _safe_div(ebit, ce_avg) * 100,
    }


def compute_utilization(canon: pd.DataFrame) -> dict[str, pd.Series]:
    rev  = _row(canon, "revenue")
    ta   = _row(canon, "total_assets")
    fa   = _row(canon, "fixed_assets")
    inv  = _row(canon, "inventories")
    rec  = _row(canon, "receivables")
    pay  = _row(canon, "trade_payables")

    ta_avg  = _avg(ta)
    fa_avg  = _avg(fa)
    inv_avg = _avg(inv)
    rec_avg = _avg(rec)
    pay_avg = _avg(pay)

    # Days calculations use 365
    dio = _safe_div(inv_avg * 365, rev)   # Days Inventory Outstanding
    dso = _safe_div(rec_avg * 365, rev)   # Days Sales Outstanding
    dpo = _safe_div(pay_avg * 365, rev)   # Days Payable Outstanding
    ccc = dio + dso - dpo                 # Cash Conversion Cycle

    return {
        "Asset Turnover (x)":               _safe_div(rev, ta_avg),
        "Fixed Asset Turnover (x)":         _safe_div(rev, fa_avg),
        "Inventory Turnover (x)":           _safe_div(rev, inv_avg),
        "Receivables Turnover (x)":         _safe_div(rev, rec_avg),
        "Days Inventory Outstanding (days)": dio,
        "Days Sales Outstanding (days)":     dso,
        "Days Payable Outstanding (days)":   dpo,
        "Cash Conversion Cycle (days)":      ccc,
    }


def compute_liquidity(canon: pd.DataFrame) -> dict[str, pd.Series]:
    ca  = _row(canon, "total_current_assets")
    cl  = _row(canon, "total_current_liab")
    inv = _row(canon, "inventories")
    csh = _row(canon, "cash")

    return {
        "Current Ratio (x)":    _safe_div(ca, cl),
        "Quick Ratio (x)":      _safe_div(ca - inv, cl),
        "Cash Ratio (x)":       _safe_div(csh, cl),
    }


def compute_solvency(canon: pd.DataFrame) -> dict[str, pd.Series]:
    borr = _row(canon, "total_borrowings")
    eq   = _row(canon, "total_equity")
    ta   = _row(canon, "total_assets")
    ebit = _row(canon, "ebit")
    int_ = _row(canon, "interest")
    csh  = _row(canon, "cash")
    ebitda = _row(canon, "ebitda")

    net_debt = borr - csh

    return {
        "Debt-to-Equity (x)":       _safe_div(borr, eq),
        "Debt-to-Assets (x)":       _safe_div(borr, ta),
        "Interest Coverage (x)":    _safe_div(ebit, int_),
        "Net Debt (₹ Cr)":          net_debt,
        "Net Debt / EBITDA (x)":    _safe_div(net_debt, ebitda),
    }


def compute_cashflow(canon: pd.DataFrame) -> dict[str, pd.Series]:
    rev   = _row(canon, "revenue")
    cfo   = _row(canon, "cfo")
    capex = _row(canon, "capex").abs()
    ni    = _row(canon, "net_income")

    fcf      = cfo - capex
    fcf_ni   = _safe_div(fcf, ni)     # FCF conversion ratio

    return {
        "Operating CF Margin (%)":      _safe_div(cfo, rev) * 100,
        "Free Cash Flow (₹ Cr)":        fcf,
        "FCF Margin (%)":               _safe_div(fcf, rev) * 100,
        "FCF to Net Income (x)":        fcf_ni,
        "CapEx Intensity (%)":          _safe_div(capex, rev) * 100,
    }


def compute_growth(canon: pd.DataFrame) -> dict[str, pd.Series]:
    rev  = _row(canon, "revenue")
    ni   = _row(canon, "net_income")
    ebitda = _row(canon, "ebitda")
    eps  = _row(canon, "eps")
    cfo  = _row(canon, "cfo")

    return {
        "Revenue Growth (%)":       rev.pct_change() * 100,
        "EBITDA Growth (%)":        ebitda.pct_change() * 100,
        "Net Income Growth (%)":    ni.pct_change() * 100,
        "EPS Growth (%)":           eps.pct_change() * 100,
        "CFO Growth (%)":           cfo.pct_change() * 100,
    }