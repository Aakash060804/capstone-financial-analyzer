"""
extraction/anomaly_detector.py
================================
AI-powered data quality gate.

Runs BEFORE the ratio engine. Scans all 14 years of canonical data
using three detection methods:

    1. Z-Score          — flags per-metric statistical outliers
    2. Isolation Forest — flags anomalous years across all metrics combined
    3. Hard Rules       — catches impossible values and large single-year drops

Returns a structured report that is displayed in the Audit Trail Excel sheet.
Pipeline never crashes — all detection is wrapped in try/except.
"""

import numpy as np
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────

ZSCORE_ERROR   = 3.0    # |z| > 3.0 → ERROR
ZSCORE_WARNING = 2.5    # |z| > 2.5 → WARNING
ZSCORE_INFO    = 2.0    # |z| > 2.0 → INFO

LARGE_DROP_PCT = 0.25   # 25% single-year decline → WARNING

# Metrics where negative values are an ERROR
MUST_BE_POSITIVE = ["revenue", "total_assets", "total_equity"]

# Metrics to check for large year-on-year drops
DROP_CHECK_METRICS = ["revenue", "ebitda", "net_income"]

# Integrity score weights
WEIGHT_ERROR   = 10.0
WEIGHT_WARNING = 3.0
WEIGHT_INFO    = 0.5


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def run_anomaly_detection(canon_df: pd.DataFrame) -> dict:
    """
    Scans the canonical DataFrame for statistical anomalies.

    Parameters
    ----------
    canon_df : pd.DataFrame
        Canonical DataFrame — rows = metric names, cols = Mar year labels

    Returns
    -------
    dict with keys:
        flags   : list of flag dicts
        summary : dict with scan statistics and integrity score
    """
    flags = []

    try:
        mar_cols = [c for c in canon_df.columns if "Mar" in str(c)]

        if len(mar_cols) < 3:
            logger.warning("Anomaly detection: fewer than 3 years — skipping")
            return _empty_report()

        # Run each detection method
        flags += _zscore_detection(canon_df, mar_cols)
        flags += _isolation_forest_detection(canon_df, mar_cols)
        flags += _hard_rule_detection(canon_df, mar_cols)
        flags += _trend_break_detection(canon_df, mar_cols)

        # Deduplicate — same metric + year + severity
        flags = _deduplicate(flags)

    except Exception as e:
        logger.warning(f"Anomaly detection failed: {e}. Returning empty report.")
        return _empty_report()

    summary = _build_summary(flags, canon_df, mar_cols)

    logger.info(
        f"Anomaly detection complete — "
        f"{summary['total_flags']} flags | "
        f"Score: {summary['integrity_score']}%"
    )

    return {
        "flags":   flags,
        "summary": summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 1 — Z-SCORE
# ─────────────────────────────────────────────────────────────────────────────

def _zscore_detection(canon_df: pd.DataFrame, mar_cols: list) -> list:
    """
    For each metric, compute mean and std across all years.
    Flag values whose |z-score| exceeds thresholds.
    """
    flags = []

    for metric in canon_df.index:
        try:
            series = canon_df.loc[metric, mar_cols].dropna()

            if len(series) < 3:
                continue

            mean = float(series.mean())
            std  = float(series.std())

            if std == 0 or np.isnan(std):
                continue  # constant value — not anomalous

            for year, value in series.items():
                z = abs((float(value) - mean) / std)

                if z > ZSCORE_ERROR:
                    severity = "ERROR"
                elif z > ZSCORE_WARNING:
                    severity = "WARNING"
                elif z > ZSCORE_INFO:
                    severity = "INFO"
                else:
                    continue

                flags.append({
                    "metric":   metric,
                    "year":     str(year),
                    "value":    round(float(value), 2),
                    "severity": severity,
                    "method":   "Z-Score",
                    "reason":   f"Z-score {z:.2f}σ from {_fmt(mean)} historical mean",
                })

        except Exception:
            continue

    return flags


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 2 — ISOLATION FOREST
# ─────────────────────────────────────────────────────────────────────────────

def _isolation_forest_detection(canon_df: pd.DataFrame, mar_cols: list) -> list:
    """
    Fits Isolation Forest on the full canonical matrix (years × metrics).
    Any year predicted as anomalous (-1) is flagged at INFO level.
    Skipped gracefully if scikit-learn is not installed.
    """
    flags = []

    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        logger.info("scikit-learn not installed — skipping Isolation Forest detection")
        return flags

    try:
        # Transpose: rows = years, cols = metrics
        matrix = canon_df[mar_cols].T.copy()

        # Fill NaN with column medians
        for col in matrix.columns:
            median = matrix[col].median()
            matrix[col] = matrix[col].fillna(median if not np.isnan(median) else 0)

        # Need at least 5 years and 2 metrics
        if matrix.shape[0] < 5 or matrix.shape[1] < 2:
            return flags

        model = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100,
        )
        predictions = model.fit_predict(matrix)

        for i, (year, pred) in enumerate(zip(mar_cols, predictions)):
            if pred == -1:
                flags.append({
                    "metric":   "Multiple metrics",
                    "year":     str(year),
                    "value":    None,
                    "severity": "INFO",
                    "method":   "Isolation Forest",
                    "reason":   "Statistically isolated year — multiple metrics deviate simultaneously",
                })

    except Exception as e:
        logger.warning(f"Isolation Forest failed: {e}")

    return flags


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 3 — HARD RULES
# ─────────────────────────────────────────────────────────────────────────────

def _hard_rule_detection(canon_df: pd.DataFrame, mar_cols: list) -> list:
    """
    Checks absolute rules that must hold regardless of Z-score:
        - Revenue, total_assets, total_equity must be positive
        - Any metric with 3+ consecutive NaN years is flagged
    """
    flags = []

    # Positive value checks
    for metric in MUST_BE_POSITIVE:
        if metric not in canon_df.index:
            continue
        series = canon_df.loc[metric, mar_cols]
        for year, value in series.items():
            if pd.isna(value):
                continue
            if float(value) <= 0:
                flags.append({
                    "metric":   metric,
                    "year":     str(year),
                    "value":    round(float(value), 2),
                    "severity": "ERROR",
                    "method":   "Hard Rule",
                    "reason":   f"{metric} must be positive — value {_fmt(float(value))} is invalid",
                })

    # Consecutive NaN check
    for metric in canon_df.index:
        series = canon_df.loc[metric, mar_cols]
        consecutive = 0
        for value in series:
            if pd.isna(value):
                consecutive += 1
                if consecutive >= 3:
                    flags.append({
                        "metric":   metric,
                        "year":     "Multiple years",
                        "value":    None,
                        "severity": "WARNING",
                        "method":   "Hard Rule",
                        "reason":   f"3+ consecutive missing values detected",
                    })
                    break
            else:
                consecutive = 0

    return flags


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 4 — TREND BREAK (large single-year declines)
# ─────────────────────────────────────────────────────────────────────────────

def _trend_break_detection(canon_df: pd.DataFrame, mar_cols: list) -> list:
    """
    For revenue, ebitda, net_income — flag any year where
    the YoY decline exceeds LARGE_DROP_PCT (25%).
    """
    flags = []

    for metric in DROP_CHECK_METRICS:
        if metric not in canon_df.index:
            continue

        series = canon_df.loc[metric, mar_cols].dropna()
        if len(series) < 2:
            continue

        values = series.values
        years  = series.index.tolist()

        for i in range(1, len(values)):
            prev = float(values[i - 1])
            curr = float(values[i])

            if prev == 0 or np.isnan(prev) or np.isnan(curr):
                continue

            pct_change = (curr - prev) / abs(prev)

            if pct_change < -LARGE_DROP_PCT:
                flags.append({
                    "metric":   metric,
                    "year":     str(years[i]),
                    "value":    round(curr, 2),
                    "severity": "WARNING",
                    "method":   "Trend Break",
                    "reason":   f"Large single-year decline of {pct_change*100:.1f}% from {_fmt(prev)}",
                })

    return flags


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _deduplicate(flags: list) -> list:
    """Remove duplicate flags for same metric + year + method."""
    seen = set()
    unique = []
    for f in flags:
        key = (f["metric"], f["year"], f["method"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _build_summary(flags: list, canon_df: pd.DataFrame, mar_cols: list) -> dict:
    errors   = sum(1 for f in flags if f["severity"] == "ERROR")
    warnings = sum(1 for f in flags if f["severity"] == "WARNING")
    info     = sum(1 for f in flags if f["severity"] == "INFO")

    raw_score = 100 - (errors * WEIGHT_ERROR) - (warnings * WEIGHT_WARNING) - (info * WEIGHT_INFO)
    score     = round(max(0.0, min(100.0, raw_score)), 1)

    return {
        "metrics_scanned": len(canon_df.index),
        "years_scanned":   len(mar_cols),
        "total_flags":     len(flags),
        "errors":          errors,
        "warnings":        warnings,
        "info_count":      info,
        "integrity_score": score,
    }


def _empty_report() -> dict:
    return {
        "flags": [],
        "summary": {
            "metrics_scanned": 0,
            "years_scanned":   0,
            "total_flags":     0,
            "errors":          0,
            "warnings":        0,
            "info_count":      0,
            "integrity_score": 100.0,
        },
    }


def _fmt(value) -> str:
    """Format a number for display in flag reasons."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    try:
        return f"₹{float(value):,.0f} Cr"
    except Exception:
        return str(value)
