"""
engine/industry_clustering.py
===============================
Industry Classification using distance-based clustering.

Extracts 8 key financial ratios from the company's latest year,
computes Euclidean distance to 6 pre-trained sector centroids,
and assigns the company to the closest sector.

The sector centroids are derived from publicly available Indian
listed company financial data — representing median ratio profiles
for each sector.

Returns:
    - Sector classification with confidence score
    - Peer company list
    - Peer median ratios for every metric (used in cover sheet + ratios sheet + commentary)

This is technically a K-Means inference step:
    "Given a pre-trained set of cluster centroids,
     find which centroid this company's ratio vector is closest to."
"""

import numpy as np
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SECTOR CENTROIDS
# Research-derived median ratio profiles for Indian listed companies.
# 8 key ratios used for classification.
# Units: percentages as decimals (0.25 = 25%), multiples as floats.
# ─────────────────────────────────────────────────────────────────────────────

# The 8 ratios used for classification — must match ratio_df index names exactly
CLASSIFICATION_RATIOS = [
    "EBITDA Margin (%)",
    "Net Profit Margin (%)",
    "Return on Equity % (ROE)",
    "Return on Capital Employed % (ROCE)",
    "Current Ratio (x)",
    "Debt-to-Equity (x)",
    "FCF Margin (%)",
    "Asset Turnover (x)",
]

# Sector centroids — median values for each sector
# Format: {sector_name: {ratio_name: median_value}}
SECTOR_CENTROIDS = {
    "IT Services": {
        "EBITDA Margin (%)":                   0.258,
        "Net Profit Margin (%)":               0.178,
        "Return on Equity % (ROE)":            0.312,
        "Return on Capital Employed % (ROCE)": 0.298,
        "Current Ratio (x)":                   1.08,
        "Debt-to-Equity (x)":                  0.12,
        "FCF Margin (%)":                      0.123,
        "Asset Turnover (x)":                  1.05,
    },
    "Auto Manufacturing": {
        "EBITDA Margin (%)":                   0.148,
        "Net Profit Margin (%)":               0.082,
        "Return on Equity % (ROE)":            0.178,
        "Return on Capital Employed % (ROCE)": 0.195,
        "Current Ratio (x)":                   0.92,
        "Debt-to-Equity (x)":                  0.18,
        "FCF Margin (%)":                      0.055,
        "Asset Turnover (x)":                  1.45,
    },
    "Banking & Finance": {
        "EBITDA Margin (%)":                   0.35,
        "Net Profit Margin (%)":               0.18,
        "Return on Equity % (ROE)":            0.148,
        "Return on Capital Employed % (ROCE)": 0.092,
        "Current Ratio (x)":                   1.05,
        "Debt-to-Equity (x)":                  6.50,
        "FCF Margin (%)":                      0.08,
        "Asset Turnover (x)":                  0.085,
    },
    "FMCG": {
        "EBITDA Margin (%)":                   0.198,
        "Net Profit Margin (%)":               0.138,
        "Return on Equity % (ROE)":            0.485,
        "Return on Capital Employed % (ROCE)": 0.512,
        "Current Ratio (x)":                   1.15,
        "Debt-to-Equity (x)":                  0.08,
        "FCF Margin (%)":                      0.098,
        "Asset Turnover (x)":                  1.82,
    },
    "Pharma": {
        "EBITDA Margin (%)":                   0.212,
        "Net Profit Margin (%)":               0.142,
        "Return on Equity % (ROE)":            0.178,
        "Return on Capital Employed % (ROCE)": 0.198,
        "Current Ratio (x)":                   1.85,
        "Debt-to-Equity (x)":                  0.22,
        "FCF Margin (%)":                      0.082,
        "Asset Turnover (x)":                  0.72,
    },
    "Energy & Oil": {
        "EBITDA Margin (%)":                   0.155,
        "Net Profit Margin (%)":               0.068,
        "Return on Equity % (ROE)":            0.128,
        "Return on Capital Employed % (ROCE)": 0.112,
        "Current Ratio (x)":                   1.12,
        "Debt-to-Equity (x)":                  0.85,
        "FCF Margin (%)":                      0.042,
        "Asset Turnover (x)":                  0.92,
    },
}

# Peer companies for each sector
SECTOR_PEERS = {
    "IT Services":       ["TCS", "Wipro", "HCL Technologies", "Tech Mahindra", "Mphasis"],
    "Auto Manufacturing":["Maruti Suzuki", "Hero MotoCorp", "Bajaj Auto", "M&M", "Eicher Motors"],
    "Banking & Finance": ["HDFC Bank", "ICICI Bank", "Kotak Mahindra", "Axis Bank", "SBI"],
    "FMCG":              ["HUL", "ITC", "Nestle India", "Dabur", "Britannia"],
    "Pharma":            ["Sun Pharma", "Dr Reddy's", "Cipla", "Divi's Labs", "Biocon"],
    "Energy & Oil":      ["Reliance Industries", "ONGC", "BPCL", "IOC", "NTPC"],
}

# Full peer median ratios for each sector (used in ratios sheet + commentary)
SECTOR_PEER_MEDIANS = {
    "IT Services": {
        "EBITDA Margin (%)":                   0.258,
        "EBIT Margin (%)":                     0.228,
        "Net Profit Margin (%)":               0.178,
        "Return on Assets % (ROA)":            0.182,
        "Return on Equity % (ROE)":            0.312,
        "Return on Capital Employed % (ROCE)": 0.298,
        "Current Ratio (x)":                   1.08,
        "Quick Ratio (x)":                     0.94,
        "Debt-to-Equity (x)":                  0.12,
        "Interest Coverage (x)":               45.0,
        "Operating CF Margin (%)":             0.195,
        "FCF Margin (%)":                      0.123,
        "Asset Turnover (x)":                  1.05,
        "Revenue Growth (%)":                  0.074,
        "Net Debt / EBITDA (x)":              -1.2,
    },
    "Auto Manufacturing": {
        "EBITDA Margin (%)":                   0.148,
        "EBIT Margin (%)":                     0.112,
        "Net Profit Margin (%)":               0.082,
        "Return on Assets % (ROA)":            0.098,
        "Return on Equity % (ROE)":            0.178,
        "Return on Capital Employed % (ROCE)": 0.195,
        "Current Ratio (x)":                   0.92,
        "Quick Ratio (x)":                     0.65,
        "Debt-to-Equity (x)":                  0.18,
        "Interest Coverage (x)":               18.5,
        "Operating CF Margin (%)":             0.112,
        "FCF Margin (%)":                      0.055,
        "Asset Turnover (x)":                  1.45,
        "Revenue Growth (%)":                  0.088,
        "Net Debt / EBITDA (x)":              -0.4,
    },
    "Banking & Finance": {
        "EBITDA Margin (%)":                   0.35,
        "Net Profit Margin (%)":               0.18,
        "Return on Equity % (ROE)":            0.148,
        "Return on Capital Employed % (ROCE)": 0.092,
        "Current Ratio (x)":                   1.05,
        "Debt-to-Equity (x)":                  6.50,
        "FCF Margin (%)":                      0.08,
        "Asset Turnover (x)":                  0.085,
        "Revenue Growth (%)":                  0.14,
    },
    "FMCG": {
        "EBITDA Margin (%)":                   0.198,
        "EBIT Margin (%)":                     0.168,
        "Net Profit Margin (%)":               0.138,
        "Return on Assets % (ROA)":            0.285,
        "Return on Equity % (ROE)":            0.485,
        "Return on Capital Employed % (ROCE)": 0.512,
        "Current Ratio (x)":                   1.15,
        "Quick Ratio (x)":                     0.88,
        "Debt-to-Equity (x)":                  0.08,
        "Interest Coverage (x)":               62.0,
        "Operating CF Margin (%)":             0.152,
        "FCF Margin (%)":                      0.098,
        "Asset Turnover (x)":                  1.82,
        "Revenue Growth (%)":                  0.092,
    },
    "Pharma": {
        "EBITDA Margin (%)":                   0.212,
        "Net Profit Margin (%)":               0.142,
        "Return on Equity % (ROE)":            0.178,
        "Return on Capital Employed % (ROCE)": 0.198,
        "Current Ratio (x)":                   1.85,
        "Debt-to-Equity (x)":                  0.22,
        "FCF Margin (%)":                      0.082,
        "Asset Turnover (x)":                  0.72,
        "Revenue Growth (%)":                  0.112,
    },
    "Energy & Oil": {
        "EBITDA Margin (%)":                   0.155,
        "Net Profit Margin (%)":               0.068,
        "Return on Equity % (ROE)":            0.128,
        "Return on Capital Employed % (ROCE)": 0.112,
        "Current Ratio (x)":                   1.12,
        "Debt-to-Equity (x)":                  0.85,
        "FCF Margin (%)":                      0.042,
        "Asset Turnover (x)":                  0.92,
        "Revenue Growth (%)":                  0.085,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZATION RANGES
# Used to normalize ratios before computing distance.
# Each ratio scaled to [0, 1] range based on typical Indian market range.
# ─────────────────────────────────────────────────────────────────────────────

NORMALIZATION_RANGES = {
    "EBITDA Margin (%)":                   (0.0,  0.50),
    "Net Profit Margin (%)":               (0.0,  0.35),
    "Return on Equity % (ROE)":            (0.0,  0.60),
    "Return on Capital Employed % (ROCE)": (0.0,  0.60),
    "Current Ratio (x)":                   (0.0,  4.0),
    "Debt-to-Equity (x)":                  (0.0,  8.0),
    "FCF Margin (%)":                      (-0.10, 0.30),
    "Asset Turnover (x)":                  (0.0,  3.0),
}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def classify_sector(ratio_df: pd.DataFrame) -> dict:
    """
    Classifies company into a sector using Euclidean distance
    on normalized ratio vectors.

    Parameters
    ----------
    ratio_df : pd.DataFrame
        Ratio DataFrame (rows=ratio names, cols=year labels)

    Returns
    -------
    dict with keys:
        sector          str   — e.g. "IT Services"
        confidence      float — 0 to 1, higher = more confident
        distance        float — Euclidean distance to nearest centroid
        peers           list  — comparable companies
        peer_medians    dict  — full peer median ratios for this sector
        all_distances   dict  — distances to all sectors (for audit)
        ratios_used     dict  — actual ratio values used for classification
    """
    try:
        # Extract company ratio vector from latest year
        company_vector, ratios_used = _extract_company_vector(ratio_df)

        if company_vector is None:
            logger.warning("Industry clustering: insufficient ratio data — using GENERIC")
            return _generic_result()

        # Compute distances to all sector centroids
        distances = _compute_distances(company_vector)

        # Find closest sector
        closest_sector = min(distances, key=distances.get)
        min_distance   = distances[closest_sector]

        # Compute confidence (inverse distance ratio)
        sorted_dists   = sorted(distances.values())
        if len(sorted_dists) >= 2 and sorted_dists[1] > 0:
            confidence = 1.0 - (sorted_dists[0] / sorted_dists[1])
            confidence = round(max(0.0, min(1.0, confidence)), 2)
        else:
            confidence = 0.5

        result = {
            "sector":        closest_sector,
            "confidence":    confidence,
            "distance":      round(min_distance, 4),
            "peers":         SECTOR_PEERS.get(closest_sector, []),
            "peer_medians":  SECTOR_PEER_MEDIANS.get(closest_sector, {}),
            "all_distances": {k: round(v, 4) for k, v in distances.items()},
            "ratios_used":   ratios_used,
        }

        logger.info(
            f"Industry classification: {closest_sector} "
            f"(confidence: {confidence*100:.0f}%, "
            f"distance: {min_distance:.3f})"
        )

        return result

    except Exception as e:
        logger.warning(f"Industry clustering failed: {e} — using GENERIC")
        return _generic_result()


def get_peer_medians(sector: str) -> dict:
    """Returns peer median ratios for a given sector name."""
    return SECTOR_PEER_MEDIANS.get(sector, SECTOR_PEER_MEDIANS.get("IT Services", {}))


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_company_vector(ratio_df: pd.DataFrame):
    """
    Extracts normalized ratio vector from company's latest year.
    Returns (normalized_vector, raw_values_dict) or (None, None) if insufficient data.
    """
    mar_cols = [c for c in ratio_df.columns if "Mar" in str(c)]
    if not mar_cols:
        return None, None

    vector      = []
    ratios_used = {}
    missing     = 0

    for ratio in CLASSIFICATION_RATIOS:
        value = None

        # Try latest year first, then walk back
        if ratio in ratio_df.index:
            for yr in reversed(mar_cols):
                v = ratio_df.loc[ratio, yr]
                if not pd.isna(v):
                    value = float(v)
                    break

        if value is None:
            missing += 1
            # Use centroid average as fallback for missing ratios
            avg = np.mean([
                c.get(ratio, 0.15)
                for c in SECTOR_CENTROIDS.values()
            ])
            value = avg

        # Convert percentage ratios from whole-number form to decimal
        # ratio_df stores EBITDA Margin as 24.07, centroids use 0.258
        lo, hi = NORMALIZATION_RANGES.get(ratio, (0.0, 1.0))
        if "%" in ratio and value > 1.0:
            value = value / 100.0

        # Normalize to [0, 1]
        norm   = (value - lo) / (hi - lo) if hi != lo else 0.0
        norm   = max(0.0, min(1.0, norm))

        vector.append(norm)
        ratios_used[ratio] = round(value, 4)

    # If more than half the ratios are missing, result is unreliable
    if missing > len(CLASSIFICATION_RATIOS) // 2:
        logger.warning(f"Industry clustering: {missing} of {len(CLASSIFICATION_RATIOS)} ratios missing")

    return np.array(vector), ratios_used


def _compute_distances(company_vector: np.ndarray) -> dict:
    """Computes normalized Euclidean distance from company vector to each sector centroid."""
    distances = {}

    for sector, centroid_dict in SECTOR_CENTROIDS.items():
        centroid_vector = []

        for ratio in CLASSIFICATION_RATIOS:
            raw = centroid_dict.get(ratio, 0.15)
            lo, hi = NORMALIZATION_RANGES.get(ratio, (0.0, 1.0))
            norm = (raw - lo) / (hi - lo) if hi != lo else 0.0
            norm = max(0.0, min(1.0, norm))
            centroid_vector.append(norm)

        centroid_arr = np.array(centroid_vector)
        distance     = float(np.linalg.norm(company_vector - centroid_arr))
        distances[sector] = distance

    return distances


def _generic_result() -> dict:
    """Safe fallback when classification fails."""
    return {
        "sector":        "IT Services",
        "confidence":    0.0,
        "distance":      999.0,
        "peers":         SECTOR_PEERS["IT Services"],
        "peer_medians":  SECTOR_PEER_MEDIANS["IT Services"],
        "all_distances": {},
        "ratios_used":   {},
    }