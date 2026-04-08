"""
forecasting/prophet_forecast.py
================================
Facebook Prophet time series forecasting.

Trains Prophet independently on 14 years of:
    - Revenue
    - EBITDA
    - Free Cash Flow

Produces 5-year forecasts with 80% confidence intervals.
Upper bound → Bull scenario
Lower bound → Bear scenario

Runs ALONGSIDE existing assumptions-based scenarios — does NOT replace them.
Results appear in a new section in the Forecasts Excel sheet with
a side-by-side comparison table.

Degrades gracefully if Prophet is not installed.
"""

import numpy as np
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)

# Metrics to forecast — canonical key → display name
METRICS_TO_FORECAST = {
    "revenue": "Revenue",
    "ebitda":  "EBITDA",
    "fcf":     "Free Cash Flow",
}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def run_prophet_forecast(canon: pd.DataFrame, forecast_years: int = 5) -> dict:
    """
    Trains Prophet on Revenue, EBITDA, and FCF from canonical data.

    Parameters
    ----------
    canon          : canonical DataFrame (rows=metrics, cols=Mar year labels)
    forecast_years : number of years to forecast ahead

    Returns
    -------
    dict with keys:
        available : bool   — False if Prophet not installed or data insufficient
        revenue   : DataFrame (rows=years, cols=[year, value, lower, upper, type])
        ebitda    : DataFrame
        fcf       : DataFrame
        summary   : dict of key forecast values for Excel display
    """
    # Check Prophet is installed
    try:
        from prophet import Prophet
    except ImportError:
        logger.warning("Prophet not installed. Run: pip install prophet")
        return {"available": False}

    mar_cols = [c for c in canon.columns if "Mar" in str(c)]
    if len(mar_cols) < 5:
        logger.warning(f"Prophet needs at least 5 years — only {len(mar_cols)} found")
        return {"available": False}

    results   = {}
    last_year = mar_cols[-1]

    try:
        base_yr = int(last_year.replace("Mar ", "").strip())
    except ValueError:
        base_yr = 2025

    # ── Compute FCF if not in canon ────────────────────────────────────────────
    if "fcf" not in canon.index and "cfo" in canon.index and "capex" in canon.index:
        cfo   = canon.loc["cfo",   mar_cols]
        capex = canon.loc["capex", mar_cols].abs()
        fcf_series = (cfo - capex)
        # Insert as temporary row
        canon = canon.copy()
        canon.loc["fcf"] = fcf_series

    # ── Run Prophet for each metric ────────────────────────────────────────────
    for key, display_name in METRICS_TO_FORECAST.items():
        try:
            if key not in canon.index:
                logger.warning(f"Prophet: {key} not in canonical data — skipping")
                continue

            series = canon.loc[key, mar_cols].dropna()

            if len(series) < 5:
                logger.warning(f"Prophet: {key} has only {len(series)} points — skipping")
                continue

            df_result = _run_single_prophet(
                series        = series,
                display_name  = display_name,
                forecast_years= forecast_years,
                base_yr       = base_yr,
            )

            results[key] = df_result
            last_forecast = df_result[df_result["type"] == "forecast"]["value"].iloc[-1]
            logger.info(
                f"Prophet [{display_name}]: "
                f"last actual ₹{float(series.iloc[-1]):,.0f} Cr → "
                f"Year {forecast_years} forecast ₹{last_forecast:,.0f} Cr"
            )

        except Exception as e:
            logger.warning(f"Prophet failed for {key}: {e}")
            continue

    if not results:
        logger.warning("Prophet: no metrics forecasted successfully")
        return {"available": False}

    # ── Build summary dict ─────────────────────────────────────────────────────
    summary = _build_summary(results, base_yr, forecast_years)

    return {
        "available":      True,
        "forecast_years": forecast_years,
        "base_yr":        base_yr,
        "summary":        summary,
        **results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE PROPHET MODEL
# ─────────────────────────────────────────────────────────────────────────────

def _run_single_prophet(
    series:         pd.Series,
    display_name:   str,
    forecast_years: int,
    base_yr:        int,
) -> pd.DataFrame:
    """
    Trains one Prophet model and returns combined actual + forecast DataFrame.

    Returns DataFrame with columns:
        year  : str   e.g. "Mar 2026"
        value : float forecast value (yhat)
        lower : float yhat_lower — bear bound
        upper : float yhat_upper — bull bound
        type  : str   "actual" or "forecast"
    """
    from prophet import Prophet
    import datetime

    # Build Prophet input
    dates = []
    for label in series.index:
        try:
            yr = int(str(label).replace("Mar ", "").strip())
            dates.append(datetime.datetime(yr, 3, 31))
        except ValueError:
            dates.append(None)

    df_prophet = pd.DataFrame({
        "ds": dates,
        "y":  series.values.astype(float),
    }).dropna()

    if len(df_prophet) < 3:
        raise ValueError(f"Insufficient data points: {len(df_prophet)}")

    # Configure Prophet for annual financial data
    model = Prophet(
        yearly_seasonality    = False,
        weekly_seasonality    = False,
        daily_seasonality     = False,
        changepoint_prior_scale = 0.3,   # moderate flexibility
        interval_width        = 0.80,    # 80% confidence interval
        uncertainty_samples   = 1000,
    )
    model.fit(df_prophet)

    # Generate future dates
    future   = model.make_future_dataframe(periods=forecast_years, freq="YE")
    forecast = model.predict(future)

    # ── Assemble output rows ───────────────────────────────────────────────────
    rows = []

    # Historical actuals
    for i, (idx, row_data) in enumerate(df_prophet.iterrows()):
        rows.append({
            "year":  series.index[i],
            "value": float(row_data["y"]),
            "lower": float(row_data["y"]),
            "upper": float(row_data["y"]),
            "type":  "actual",
        })

    # Forecast years only
    forecast_only = forecast.tail(forecast_years)
    for i, (_, frow) in enumerate(forecast_only.iterrows()):
        yr = f"Mar {base_yr + i + 1}"
        rows.append({
            "year":  yr,
            "value": max(float(frow["yhat"]),       0),
            "lower": max(float(frow["yhat_lower"]), 0),
            "upper": max(float(frow["yhat_upper"]), 0),
            "type":  "forecast",
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary(results: dict, base_yr: int, forecast_years: int) -> dict:
    """Flat summary dict for Excel comparison table."""
    summary = {}

    for key, df in results.items():
        actual_rows   = df[df["type"] == "actual"]
        forecast_rows = df[df["type"] == "forecast"]

        if not actual_rows.empty:
            summary[f"{key}_last_actual"] = float(actual_rows["value"].iloc[-1])

        for i in range(1, forecast_years + 1):
            yr  = f"Mar {base_yr + i}"
            row = forecast_rows[forecast_rows["year"] == yr]
            if not row.empty:
                summary[f"{key}_base_{yr}"]  = float(row["value"].iloc[0])
                summary[f"{key}_lower_{yr}"] = float(row["lower"].iloc[0])
                summary[f"{key}_upper_{yr}"] = float(row["upper"].iloc[0])

    return summary
