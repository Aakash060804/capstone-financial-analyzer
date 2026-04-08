"""
Sensitivity analysis — 2-variable table.
Rows: WACC range
Cols: Terminal Growth Rate range
Values: Intrinsic value per share
"""

import pandas as pd
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)


def build_sensitivity_table(dcf_result: dict) -> pd.DataFrame:
    """
    Builds a WACC × Terminal Growth Rate sensitivity table.
    Returns DataFrame: index=WACC values, columns=terminal growth values,
    values=intrinsic value per share.
    """
    # Extract DCF inputs
    base_fcf          = dcf_result["assumptions"]["Base FCF (₹ Cr)"]
    fcf_growth        = dcf_result["fcf_growth_used"] / 100
    n_years           = dcf_result["assumptions"]["Projection Years"]
    net_debt          = dcf_result["net_debt"]
    shares            = dcf_result["shares_outstanding_cr"]

    # Sensitivity ranges
    wacc_range   = [w / 100 for w in range(8, 17, 1)]    # 8% to 16%
    tgr_range    = [t / 100 for t in range(2, 7,  1)]    # 2% to 6%

    results = {}

    for wacc in wacc_range:
        row = {}
        for tgr in tgr_range:
            if wacc <= tgr:
                row[f"{tgr*100:.0f}%"] = np.nan
                continue

            # Project FCF
            fcf = base_fcf
            pv_sum = 0
            for i in range(1, n_years + 1):
                fcf    = fcf * (1 + fcf_growth)
                pv_sum += fcf / ((1 + wacc) ** i)

            # Terminal value
            terminal_fcf = fcf * (1 + tgr)
            tv           = terminal_fcf / (wacc - tgr)
            pv_tv        = tv / ((1 + wacc) ** n_years)

            ev         = pv_sum + pv_tv
            eq_val     = ev - net_debt
            per_share  = (eq_val * 1e7) / (shares * 1e7 / 5 * 5)

            row[f"{tgr*100:.0f}%"] = round(per_share, 0)

        results[f"{wacc*100:.0f}%"] = row

    df = pd.DataFrame(results).T
    df.index.name   = "WACC →  /  Terminal Growth ↓"
    df.columns.name = "Terminal Growth Rate"

    logger.info(f"Sensitivity table: {df.shape[0]} WACC levels × {df.shape[1]} TGR levels")
    return df