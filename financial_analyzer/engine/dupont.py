"""
5-Factor DuPont decomposition of Return on Equity.

ROE = Tax Burden x Interest Burden x EBIT Margin x Asset Turnover x Equity Multiplier
    = (NI/EBT)  x (EBT/EBIT)      x (EBIT/Rev)  x (Rev/Assets)  x (Assets/Equity)
"""

import pandas as pd
import numpy as np
from engine.ratios import _row, _avg, _safe_div
from utils.logger  import get_logger

logger = get_logger(__name__)


def compute_dupont(canon: pd.DataFrame) -> pd.DataFrame:
    """
    Returns DataFrame: index=factor_name, columns=years.
    Last row is the reconstructed DuPont ROE for verification.
    """
    ni   = _row(canon, "net_income")
    ebt  = _row(canon, "ebt")
    ebit = _row(canon, "ebit")
    rev  = _row(canon, "revenue")
    ta   = _row(canon, "total_assets")
    eq   = _row(canon, "total_equity")

    ta_avg = _avg(ta)
    eq_avg = _avg(eq)

    tax_burden       = _safe_div(ni,   ebt)       # NI / EBT
    interest_burden  = _safe_div(ebt,  ebit)      # EBT / EBIT
    ebit_margin      = _safe_div(ebit, rev)        # EBIT / Revenue
    asset_turnover   = _safe_div(rev,  ta_avg)     # Revenue / Avg Assets
    equity_multiplier= _safe_div(ta_avg, eq_avg)   # Avg Assets / Avg Equity

    dupont_roe = (
        tax_burden *
        interest_burden *
        ebit_margin *
        asset_turnover *
        equity_multiplier
    ) * 100

    # Direct ROE for cross-check
    direct_roe = _safe_div(ni, eq_avg) * 100

    factors = {
        "(1) Tax Burden  [NI / EBT]":               tax_burden,
        "(2) Interest Burden  [EBT / EBIT]":         interest_burden,
        "(3) EBIT Margin  [EBIT / Revenue]":          ebit_margin,
        "(4) Asset Turnover  [Revenue / Avg Assets]": asset_turnover,
        "(5) Equity Multiplier  [Avg Assets / Avg Equity]": equity_multiplier,
        "DuPont ROE (%)  [Product of above x 100]":  dupont_roe,
        "Direct ROE (%)  [NI / Avg Equity x 100]":   direct_roe,
        "Variance (DuPont vs Direct)":                dupont_roe - direct_roe,
    }

    df = pd.DataFrame(factors).T
    df.index.name = "DuPont Factor"
    logger.info(f"DuPont computed: {df.shape[0]} factors x {df.shape[1]} years")
    return df