"""
forecasting/wacc_calculator.py
================================
Dynamic WACC computation using CAPM.

Fetches beta from NSE India API for the specific company.
Derives cost of debt from actual interest expense and borrowings.
Computes capital structure weights from balance sheet.

Formula:
    WACC = (E/V x Ke) + (D/V x Kd x (1 - Tax Rate))
    Ke   = Rf + β x (Rm - Rf)      [CAPM]
"""

import numpy as np
import pandas as pd
import requests
from utils.logger import get_logger
from config.settings import (
    RISK_FREE_RATE,
    EQUITY_RISK_PREMIUM,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
)

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Sector-based beta fallbacks — used when NSE API call fails
SECTOR_BETA_FALLBACK = {
    "IT":      0.65,   # IT services — lower volatility, defensive revenue
    "AUTO":    0.85,   # Auto — moderate cyclicality
    "BANK":    1.20,   # Banking — high market sensitivity
    "FMCG":    0.55,   # FMCG — defensive, low beta
    "PHARMA":  0.70,   # Pharma — semi-defensive
    "ENERGY":  0.90,   # Oil & Gas — commodity linked
    "GENERIC": 1.00,   # Unknown sector — market average
}

# Cost of debt caps — prevent unrealistic values
KD_MIN = 0.04   # 4% floor — below this implies data error
KD_MAX = 0.14   # 14% ceiling — above this is extreme

# NSE API endpoint for equity quote data
NSE_QUOTE_URL = "https://www.nseindia.com/api/quote-equity?symbol={symbol}"
NSE_HEADERS   = {
    **REQUEST_HEADERS,
    "Referer":    "https://www.nseindia.com",
    "Accept":     "application/json",
    "Connection": "keep-alive",
}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def compute_wacc(
    canon_df:        pd.DataFrame,
    symbol:          str,
    risk_free_rate:  float = None,
) -> dict:
    """
    Computes dynamic WACC for the company.

    Parameters
    ----------
    canon_df       : canonical DataFrame (rows=metrics, cols=Mar year labels)
    symbol         : NSE ticker symbol e.g. 'INFY', 'TCS', 'MARUTI'
    risk_free_rate : override risk-free rate (uses settings.py default if None)

    Returns
    -------
    dict with keys:
        wacc                float   — final WACC as decimal e.g. 0.104
        cost_of_equity      float
        cost_of_debt        float
        beta                float
        beta_source         str     — 'NSE API' or 'Sector Fallback'
        debt_weight         float
        equity_weight       float
        risk_free_rate      float
        equity_risk_premium float
        tax_rate            float
        computation_log     list    — step-by-step explanation for Audit Trail
    """
    rf  = risk_free_rate if risk_free_rate is not None else RISK_FREE_RATE
    erp = EQUITY_RISK_PREMIUM
    log = []

    # ── Step 1: Fetch Beta ─────────────────────────────────────────────────────
    beta, beta_source = _fetch_beta(symbol)
    log.append(f"Beta: {beta:.2f} (source: {beta_source})")

    # ── Step 2: Cost of Equity via CAPM ───────────────────────────────────────
    ke = rf + beta * erp
    log.append(
        f"Cost of Equity (CAPM): {ke*100:.2f}%"
        f"  [Rf {rf*100:.1f}% + {beta:.2f} × ERP {erp*100:.1f}%]"
    )

    # ── Step 3: Cost of Debt from actual financials ────────────────────────────
    kd, kd_note = _compute_cost_of_debt(canon_df)
    log.append(f"Cost of Debt: {kd*100:.2f}%  [{kd_note}]")

    # ── Step 4: Tax rate from actuals ─────────────────────────────────────────
    tax_rate = _get_tax_rate(canon_df)
    log.append(f"Tax Rate: {tax_rate*100:.1f}%  [3-year average from tax_pct]")

    # ── Step 5: Capital structure weights ─────────────────────────────────────
    debt_weight, equity_weight, weight_note = _get_weights(canon_df)
    log.append(
        f"Capital Structure: Debt {debt_weight*100:.1f}% / "
        f"Equity {equity_weight*100:.1f}%  [{weight_note}]"
    )

    # ── Step 6: Final WACC ────────────────────────────────────────────────────
    wacc = (equity_weight * ke) + (debt_weight * kd * (1 - tax_rate))

    # Guard against NaN (e.g. missing balance sheet data) before clamping
    import math as _math
    if _math.isnan(wacc) or _math.isinf(wacc):
        from config.settings import DCF_WACC
        wacc = DCF_WACC
        log.append(f"WACC was NaN/Inf (missing data) — using settings default {DCF_WACC*100:.1f}%")

    # Sanity bounds — WACC below 6% or above 20% is likely a data error
    wacc_raw = wacc
    wacc = max(0.06, min(0.20, wacc))
    if wacc != wacc_raw:
        log.append(f"WACC clamped from {wacc_raw*100:.2f}% to {wacc*100:.2f}% (sanity bounds)")

    log.append(
        f"Dynamic WACC: {wacc*100:.2f}%"
        f"  [{equity_weight*100:.1f}% × {ke*100:.2f}%"
        f" + {debt_weight*100:.1f}% × {kd*100:.2f}% × (1 - {tax_rate*100:.1f}%)]"
    )

    logger.info(
        f"Dynamic WACC computed: {wacc*100:.2f}% "
        f"[β={beta:.2f}, Ke={ke*100:.2f}%, Kd={kd*100:.2f}%, "
        f"D/V={debt_weight*100:.1f}%]"
    )

    return {
        "wacc":                wacc,
        "cost_of_equity":      ke,
        "cost_of_debt":        kd,
        "beta":                beta,
        "beta_source":         beta_source,
        "debt_weight":         debt_weight,
        "equity_weight":       equity_weight,
        "risk_free_rate":      rf,
        "equity_risk_premium": erp,
        "tax_rate":            tax_rate,
        "computation_log":     log,
    }


# ─────────────────────────────────────────────────────────────────────────────
# BETA FETCHING
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_beta(symbol: str) -> tuple[float, str]:
    """
    Fetches beta from NSE India API.
    Falls back to sector-based estimate if API call fails.

    Returns (beta_value, source_description)
    """
    try:
        # NSE requires a session with cookies — use a session object
        session = requests.Session()

        # First hit the main NSE page to get cookies
        session.get(
            "https://www.nseindia.com",
            headers=NSE_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        # Now fetch the quote data
        url  = NSE_QUOTE_URL.format(symbol=symbol.upper())
        resp = session.get(url, headers=NSE_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        data = resp.json()

        # Beta is in priceInfo or metadata section
        beta = None
        if "metadata" in data and "beta" in data["metadata"]:
            beta = float(data["metadata"]["beta"])
        elif "priceInfo" in data and "beta" in data["priceInfo"]:
            beta = float(data["priceInfo"]["beta"])
        elif "securityInfo" in data and "beta" in data["securityInfo"]:
            beta = float(data["securityInfo"]["beta"])

        if beta is not None and 0.1 <= beta <= 3.0:
            logger.info(f"Beta fetched from NSE API: {beta:.2f} ({symbol})")
            return beta, "NSE API"
        else:
            logger.warning(f"NSE API returned invalid beta: {beta} — using fallback")

    except Exception as e:
        logger.warning(f"NSE API beta fetch failed ({e}) — using sector fallback")

    # Sector fallback
    beta, source = _sector_beta_fallback(symbol)
    return beta, source


def _sector_beta_fallback(symbol: str) -> tuple[float, str]:
    """Returns sector-based beta estimate based on company name/symbol."""
    sym = symbol.upper()

    if any(k in sym for k in ["INFY", "TCS", "WIPRO", "HCL", "TECHM", "MPHASIS", "LTIM"]):
        sector = "IT"
    elif any(k in sym for k in ["MARUTI", "TATAMOTORS", "HEROMOTOCO", "BAJAJ-AUTO", "M&M", "EICHERMOT"]):
        sector = "AUTO"
    elif any(k in sym for k in ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "BANKBARODA"]):
        sector = "BANK"
    elif any(k in sym for k in ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR", "MARICO"]):
        sector = "FMCG"
    elif any(k in sym for k in ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "BIOCON"]):
        sector = "PHARMA"
    elif any(k in sym for k in ["RELIANCE", "ONGC", "BPCL", "IOC", "GAIL", "NTPC", "POWERGRID"]):
        sector = "ENERGY"
    else:
        sector = "GENERIC"

    beta = SECTOR_BETA_FALLBACK[sector]
    logger.info(f"Using sector beta fallback: {sector} → β={beta:.2f}")
    return beta, f"Sector Fallback ({sector})"


# ─────────────────────────────────────────────────────────────────────────────
# COST OF DEBT
# ─────────────────────────────────────────────────────────────────────────────

def _compute_cost_of_debt(canon_df: pd.DataFrame) -> tuple[float, str]:
    """
    Computes cost of debt as: Interest Expense / Total Borrowings
    Uses 3-year average to smooth volatility.
    """
    mar_cols = [c for c in canon_df.columns if "Mar" in str(c)]
    recent   = mar_cols[-3:] if len(mar_cols) >= 3 else mar_cols

    try:
        if "interest" in canon_df.index and "total_borrowings" in canon_df.index:
            interest   = canon_df.loc["interest",        recent].dropna()
            borrowings = canon_df.loc["total_borrowings", recent].dropna()

            common = interest.index.intersection(borrowings.index)
            if len(common) > 0 and borrowings[common].mean() > 10:
                kd_raw = float(interest[common].mean() / borrowings[common].mean())
                kd     = max(KD_MIN, min(KD_MAX, kd_raw))
                note   = f"Interest/Borrowings 3yr avg, raw={kd_raw*100:.1f}%"
                return kd, note

    except Exception as e:
        logger.warning(f"Cost of debt computation failed: {e}")

    # Fallback — use a reasonable rate for Indian corporate debt
    kd = 0.085  # 8.5% — approximate Indian corporate bond rate
    return kd, "Fallback — Indian corporate rate 8.5%"


# ─────────────────────────────────────────────────────────────────────────────
# TAX RATE
# ─────────────────────────────────────────────────────────────────────────────

def _get_tax_rate(canon_df: pd.DataFrame) -> float:
    """3-year average effective tax rate from canonical data."""
    mar_cols = [c for c in canon_df.columns if "Mar" in str(c)]
    recent   = mar_cols[-3:] if len(mar_cols) >= 3 else mar_cols

    try:
        if "tax_pct" in canon_df.index:
            tax_series = canon_df.loc["tax_pct", recent].dropna()
            if len(tax_series) > 0:
                avg = float(tax_series.mean())
                # tax_pct stored as whole number e.g. 26 means 26%
                return avg / 100 if avg > 1 else avg
    except Exception:
        pass

    return 0.25  # 25% fallback — standard Indian corporate tax


# ─────────────────────────────────────────────────────────────────────────────
# CAPITAL STRUCTURE WEIGHTS
# ─────────────────────────────────────────────────────────────────────────────

def _get_weights(canon_df: pd.DataFrame) -> tuple[float, float, str]:
    """
    Computes debt and equity weights from balance sheet.
    Uses book value (available) as proxy for market value weights.

    Returns (debt_weight, equity_weight, note)
    """
    mar_cols = [c for c in canon_df.columns if "Mar" in str(c)]
    if not mar_cols:
        return 0.30, 0.70, "Fallback weights"

    latest = mar_cols[-1]

    try:
        debt   = float(canon_df.loc["total_borrowings", latest]) \
                if "total_borrowings" in canon_df.index else 0.0
        equity = float(canon_df.loc["total_equity",     latest]) \
                if "total_equity"     in canon_df.index else 1.0

        # Guard against NaN or negative
        debt   = max(debt,   0.0)
        equity = max(equity, 1.0)

        total         = debt + equity
        debt_weight   = debt   / total
        equity_weight = equity / total
        note          = f"Book value {latest}: D=₹{debt:,.0f}Cr, E=₹{equity:,.0f}Cr"

        return debt_weight, equity_weight, note

    except Exception as e:
        logger.warning(f"Capital structure weights failed: {e}")
        return 0.20, 0.80, "Fallback 20/80 D/E split"
