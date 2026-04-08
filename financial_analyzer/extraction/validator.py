"""
Validates the canonical DataFrame before ratios are computed.
Raises descriptive errors rather than silently producing wrong outputs.
"""

import pandas as pd
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)

# These must be present for the ratio engine to work at all
REQUIRED_METRICS = [
    "revenue",
    "net_income",
    "total_assets",
    "total_equity",
    "ebitda",
    "ebit"
]

# These should never be negative (if they are, data is likely wrong)
MUST_BE_POSITIVE = [
    "revenue",
    "total_assets",
    "total_equity",
    "inventories",
    "receivables",
]


class ValidationError(Exception):
    pass


def validate(canon: pd.DataFrame) -> list[str]:
    """
    Validates the canonical DataFrame.

    Returns a list of warning strings (non-fatal issues).
    Raises ValidationError for fatal issues that would break the engine.
    """
    warnings = []

    if canon.empty:
        raise ValidationError(
            "Canonical DataFrame is empty. "
            "Check scraper output and CANONICAL_MAP in settings.py"
        )
        
    
    # ── Fatal checks ──────────────────────────────────────────────────────────
    missing_critical = [m for m in REQUIRED_METRICS if m not in canon.index]
    if missing_critical:
        raise ValidationError(
            f"Critical metrics missing from extracted data: {missing_critical}\n"
            f"Available metrics: {list(canon.index)}"
        )

    # ── Year continuity ───────────────────────────────────────────────────────
    if canon.shape[1] < 3:
        warnings.append(
            f"Only {canon.shape[1]} year(s) of data found. "
            "CAGR and trend analysis require at least 3 years."
        )

    # ── Positive value checks ─────────────────────────────────────────────────
    for metric in MUST_BE_POSITIVE:
        if metric not in canon.index:
            continue
        series = canon.loc[metric].dropna()
        if (series <= 0).any():
            bad_years = series[series <= 0].index.tolist()
            warnings.append(
                f"'{metric}' has non-positive values in {bad_years}. "
                "Check source data."
            )

    # ── Balance sheet check: Assets ≈ Liabilities + Equity ───────────────────
    if all(m in canon.index for m in ["total_assets", "total_equity", "total_borrowings"]):
        assets  = canon.loc["total_assets"].dropna()
        equity  = canon.loc["total_equity"].dropna()
        borrows = canon.loc["total_borrowings"].dropna()
        # Rough check: assets should be > equity + borrowings (other liabilities exist)
        common_years = assets.index.intersection(equity.index).intersection(borrows.index)
        for yr in common_years:
            if assets[yr] < equity[yr]:
                warnings.append(
                    f"{yr}: Total Assets ({assets[yr]:,.0f}) < Total Equity ({equity[yr]:,.0f}). "
                    "Possible data error."
                )

    # ── Net income sign check ─────────────────────────────────────────────────
    if "net_income" in canon.index:
        ni = canon.loc["net_income"].dropna()
        loss_years = ni[ni < 0].index.tolist()
        if loss_years:
            warnings.append(f"Company reported losses in: {loss_years}")
            
    # ── Soft check for cash flow ──────────────────────────────────────────────
    soft_required = ["cfo", "capex"]
    missing_soft = [m for m in soft_required if m not in canon.index]
    if missing_soft:
        warnings.append(
            f"Cash flow metrics not found: {missing_soft}. "
            "FCF and cash flow ratios will be skipped."
        )
            

    # ── Log results ──────────────────────────────────────────────────────────
    if warnings:
        for w in warnings:
            logger.warning(f"[Validation] {w}")
    else:
        logger.info("[Validation] All checks passed")

    return warnings