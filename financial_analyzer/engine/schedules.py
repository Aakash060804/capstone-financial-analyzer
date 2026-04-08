"""
Working Capital Schedule and Debt Schedule.
These are analytical schedules — not raw data, not ratios.
They show ₹ movements year over year alongside the ratio.
"""

import pandas as pd
import numpy as np
from engine.ratios import _row, _safe_div
from utils.logger  import get_logger

logger = get_logger(__name__)


def working_capital_schedule(canon: pd.DataFrame) -> pd.DataFrame:
    """
    Builds the working capital schedule showing:
    - Gross Working Capital
    - Net Working Capital
    - Changes YoY in ₹
    - Key days metrics side by side
    """
    rev  = _row(canon, "revenue")
    inv  = _row(canon, "inventories")
    rec  = _row(canon, "receivables")
    pay  = _row(canon, "trade_payables")
    ca   = _row(canon, "total_current_assets")
    cl   = _row(canon, "total_current_liab")
    csh  = _row(canon, "cash")

    inv_avg = (inv + inv.shift(1)) / 2
    rec_avg = (rec + rec.shift(1)) / 2
    pay_avg = (pay + pay.shift(1)) / 2

    gwc     = inv + rec                              # Gross Working Capital
    nwc     = ca - cl                                # Net Working Capital
    nwc_chg = nwc - nwc.shift(1)                    # Change in NWC

    dio = _safe_div(inv_avg * 365, rev)
    dso = _safe_div(rec_avg * 365, rev)
    dpo = _safe_div(pay_avg * 365, rev)
    ccc = dio + dso - dpo

    schedule = {
        "Inventories (₹ Cr)":               inv,
        "Trade Receivables (₹ Cr)":         rec,
        "Trade Payables (₹ Cr)":            pay,
        "Gross Working Capital (₹ Cr)":     gwc,
        "Net Working Capital (₹ Cr)":       nwc,
        "Change in NWC (₹ Cr)":            nwc_chg,
        "Days Inventory Outstanding":       dio,
        "Days Sales Outstanding":           dso,
        "Days Payable Outstanding":         dpo,
        "Cash Conversion Cycle (days)":     ccc,
    }

    df = pd.DataFrame(schedule).T
    df.index.name = "Working Capital Metric"
    logger.info(f"Working capital schedule: {df.shape}")
    return df


def debt_schedule(canon: pd.DataFrame) -> pd.DataFrame:
    """
    Builds the debt schedule:
    Opening → Additions → Repayments → Closing
    Plus interest coverage and net debt metrics.
    """
    borr   = _row(canon, "total_borrowings")
    int_   = _row(canon, "interest")
    ebit   = _row(canon, "ebit")
    ebitda = _row(canon, "ebitda")
    csh    = _row(canon, "cash")
    cff    = _row(canon, "cff")

    opening    = borr.shift(1)
    closing    = borr
    net_change = closing - opening         # + means new borrowing, - means repayment

    net_debt         = borr - csh
    int_coverage     = _safe_div(ebit,   int_)
    ebitda_coverage  = _safe_div(ebitda, int_)
    net_debt_ebitda  = _safe_div(net_debt, ebitda)

    schedule = {
        "Opening Borrowings (₹ Cr)":        opening,
        "Closing Borrowings (₹ Cr)":        closing,
        "Net Change in Debt (₹ Cr)":        net_change,
        "Cash & Equivalents (₹ Cr)":        csh,
        "Net Debt (₹ Cr)":                  net_debt,
        "Interest Expense (₹ Cr)":          int_,
        "Interest Coverage - EBIT (x)":     int_coverage,
        "Interest Coverage - EBITDA (x)":   ebitda_coverage,
        "Net Debt / EBITDA (x)":            net_debt_ebitda,
        "Cash from Financing (₹ Cr)":       cff,
    }

    df = pd.DataFrame(schedule).T
    df.index.name = "Debt Schedule Metric"
    logger.info(f"Debt schedule: {df.shape}")
    return df