"""
Scenario forecasting engine.
Projects Base / Bull / Bear P&L for FORECAST_YEARS.
Uses last historical year as the base.
"""

import pandas as pd
import numpy as np
from config.settings import FORECAST_YEARS, SCENARIO_ASSUMPTIONS
from utils.logger    import get_logger

logger = get_logger(__name__)


def _last_val(canon: pd.DataFrame, key: str) -> float:
    """Get most recent non-null value for a metric."""
    if key not in canon.index:
        return np.nan
    mar_cols = [c for c in canon.columns if "Mar" in str(c)]
    vals = canon.loc[key, mar_cols].dropna()
    return float(vals.iloc[-1]) if len(vals) else np.nan


def _last_year_label(canon: pd.DataFrame) -> str:
    """Get the most recent Mar year label."""
    mar_cols = [c for c in canon.columns if "Mar" in str(c)]
    return mar_cols[-1] if mar_cols else "Mar 2024"


def _next_year_label(label: str, offset: int) -> str:
    """Convert 'Mar 2024' + 1 → 'Mar 2025'."""
    try:
        yr = int(label.replace("Mar ", "").strip())
        return f"Mar {yr + offset}"
    except ValueError:
        return f"Year +{offset}"


def build_scenarios(canon: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Returns:
        {
            "base": pd.DataFrame,
            "bull": pd.DataFrame,
            "bear": pd.DataFrame,
        }
    Each DataFrame: index=metric, columns=forecast year labels
    """
    results = {}
    for scenario, assumptions in SCENARIO_ASSUMPTIONS.items():
        df = _project(canon, assumptions, scenario)
        results[scenario] = df
        last_rev = df.loc["Revenue", df.columns[-1]]
        logger.info(
            f"Scenario [{scenario:4s}]: "
            f"{FORECAST_YEARS}-year projection, "
            f"last revenue → ₹{last_rev:,.0f} Cr"
        )
    return results


def _project(
    canon: pd.DataFrame,
    assumptions: dict,
    label: str,
) -> pd.DataFrame:

    rev_growth      = assumptions["revenue_growth"]
    ebit_mgn_delta  = assumptions["ebit_margin_delta"]
    tax_rate        = assumptions["tax_rate"]

    # Base values from last historical year
    base_rev        = _last_val(canon, "revenue")
    base_ebit_margin= _last_val(canon, "ebit") / _last_val(canon, "revenue") if _last_val(canon, "revenue") else 0.12
    base_dep        = _last_val(canon, "depreciation")
    base_interest   = _last_val(canon, "interest")
    base_cfo        = _last_val(canon, "cfo")
    base_capex      = abs(_last_val(canon, "capex"))
    base_equity     = _last_val(canon, "total_equity")

    target_ebit_margin = base_ebit_margin + ebit_mgn_delta

    last_yr  = _last_year_label(canon)
    rows     = {}
    rev      = base_rev
    equity   = base_equity

    for i in range(1, FORECAST_YEARS + 1):
        yr      = _next_year_label(last_yr, i)
        rev     = rev * (1 + rev_growth)
        ebit    = rev * target_ebit_margin
        dep     = base_dep * (1.05 ** i)           # 5% annual depreciation growth
        ebitda  = ebit + dep
        ebt     = ebit - base_interest
        ni      = max(ebt * (1 - tax_rate), 0)     # floor at 0
        capex   = base_capex * (1.05 ** i)
        cfo_est = base_cfo * ((1 + rev_growth) ** i)
        fcf     = cfo_est - capex
        equity  = equity + ni                       # simplified: retained earnings added

        rows[yr] = {
            "Revenue":              round(rev,         0),
            "Expenses (est.)":      round(rev - ebitda, 0),
            "Operating Profit":     round(ebitda,       0),
            "OPM %":                round(ebitda / rev * 100, 1),
            "Other Income":         round(base_interest * 0.5, 0),  # conservative estimate
            "Interest":             round(base_interest, 0),
            "Depreciation":         round(dep,           0),
            "Profit before tax":    round(ebt,           0),
            "Tax %":                round(tax_rate * 100, 1),
            "Net Income":           round(ni,            0),
            "CapEx":                round(capex,         0),
            "Operating Cash Flow":  round(cfo_est,       0),
            "Free Cash Flow":       round(fcf,           0),
            "EBITDA Margin (%)":    round(ebitda / rev * 100, 2),
            "Net Margin (%)":       round(ni     / rev * 100, 2),
            "FCF Margin (%)":       round(fcf    / rev * 100, 2),
            "ROE (%) est.":         round(ni / equity * 100,  2),
            "Revenue Growth (%)":   round(rev_growth * 100,   1),
        }

    df = pd.DataFrame(rows)
    df.index.name = "Metric"
    return df

