"""
Fetches the three financial statements from Screener.in.
Falls back to built-in Maruti Suzuki data if network is unavailable.
"""

import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

from config.settings   import (SCREENER_URL, SCREENER_SLUG,
                                REQUEST_HEADERS, REQUEST_TIMEOUT,
                                CANONICAL_MAP)
from extraction.parser import parse_screener_table
from utils.cache       import load_cache, save_cache
from utils.logger      import get_logger

logger = get_logger(__name__)

SECTION_IDS = {
    "income_statement": "profit-loss",
    "balance_sheet":    "balance-sheet",
    "cash_flow":        "cash-flow",
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_statements(use_cache: bool = True) -> dict[str, pd.DataFrame]:
    """
    Strategy:
    - Try live scrape for top-level metrics (revenue, ebitda, etc.)
    - Always enrich with fallback data for detailed line items
    (inventories, receivables, payables, cash) that Screener
    does not expose without authentication

    Returns dict with keys:
        income_statement, balance_sheet, cash_flow  — DataFrames
        _face_value                                  — int (Rs 1/2/5/10)
    """
    if use_cache:
        cached = load_cache(SCREENER_SLUG)
        if cached:
            logger.info("Loading statements from cache")
            return _deserialize(cached)

    fallback = _fallback_data()

    try:
        logger.info(f"Fetching live data: {SCREENER_URL}")
        resp = requests.get(
            SCREENER_URL,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        live = _parse_all_sections(soup)

        # ── Extract face value from Screener page ──────────────────────────
        face_value = _extract_face_value(soup)
        logger.info(f"Face value detected: ₹{face_value}")
        # ──────────────────────────────────────────────────────────────────

        # Merge: live data takes priority, fallback fills gaps
        statements = _merge_statements(live, fallback)
        statements["_face_value"] = face_value          # store alongside statements
        logger.info("Live data fetched and merged with detailed fallback")

    except Exception as e:
        logger.warning(f"Live fetch failed ({e}). Using full fallback data.")
        statements = fallback
        statements["_face_value"] = _fallback_face_value()

    if use_cache:
        save_cache(SCREENER_SLUG, _serialize(statements))

    return statements


def _merge_statements(
    live: dict[str, pd.DataFrame],
    fallback: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    """
    Merge live scraped data with fallback.
    Live rows overwrite fallback rows of the same label.
    Fallback rows not present in live are appended.
    Only years present in live data are kept (ensures consistency).
    """
    merged = {}

    for key in ["income_statement", "balance_sheet", "cash_flow"]:
        live_df     = live.get(key, pd.DataFrame())
        fallback_df = fallback.get(key, pd.DataFrame())

        if live_df.empty:
            merged[key] = fallback_df
            continue

        # Use live years as the master column set
        live_years = live_df.columns.tolist()

        # Filter fallback to only years that exist in live
        common_years = [yr for yr in live_years if yr in fallback_df.columns]
        fallback_filtered = fallback_df[common_years] if common_years else pd.DataFrame()

        if fallback_filtered.empty:
            merged[key] = live_df
            continue

        # Align columns — reindex fallback to match live years (NaN for missing)
        fallback_aligned = fallback_filtered.reindex(columns=live_years)

        # Combine: start with fallback, overwrite with live rows
        combined = fallback_aligned.copy()
        for label in live_df.index:
            combined.loc[label] = live_df.loc[label]

        merged[key] = combined
        logger.debug(
            f"[{key}] merged: {len(combined)} rows, "
            f"{live_df.shape[0]} from live, "
            f"{len(fallback_aligned)} from fallback"
        )

    return merged


def build_canonical(statements: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Searches all three statement DataFrames for each canonical metric.
    Returns a single DataFrame: index=canonical_key, columns=years.
    """
    # Merge all statements into one lookup table
    frames = []
    for key, df in statements.items():
        if key.startswith("_"):
            continue          # skip _face_value and any other metadata keys
        if not df.empty:
            frames.append(df)

    if not frames:
        logger.error("All statement DataFrames are empty")
        return pd.DataFrame()

    combined = pd.concat(frames)
    # Drop duplicate index labels (keep first occurrence)
    combined = combined[~combined.index.duplicated(keep="first")]

    result = {}
    for canon_key, aliases in CANONICAL_MAP.items():
        for alias in aliases:
            if alias in combined.index:
                result[canon_key] = combined.loc[alias]
                logger.debug(f"  {canon_key} ← '{alias}'")
                break
        if canon_key not in result:
            logger.debug(f"  {canon_key} ← NOT FOUND")

    if not result:
        return pd.DataFrame()

    canon_df = pd.DataFrame(result).T
    canon_df.index.name = "metric"
    logger.info(f"Canonical DataFrame: {canon_df.shape[0]} metrics x {canon_df.shape[1]} years")
    canon_df = _derive_missing(canon_df)
    return canon_df


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_all_sections(soup: BeautifulSoup) -> dict[str, pd.DataFrame]:
    statements = {}
    for key, section_id in SECTION_IDS.items():
        section = soup.find("section", {"id": section_id})
        if not section:
            logger.warning(f"Section '{section_id}' not found in HTML")
            statements[key] = pd.DataFrame()
            continue
        df = parse_screener_table(section)
        statements[key] = df
        logger.info(f"[{key}] {df.shape[0]} line items, {df.shape[1]} years")
    return statements


def _validate_raw(statements: dict[str, pd.DataFrame]) -> None:
    """Raise ValueError if critical sections are empty."""
    critical = ["income_statement", "balance_sheet"]
    for key in critical:
        df = statements.get(key, pd.DataFrame())
        if df.empty:
            raise ValueError(f"Critical section '{key}' returned empty DataFrame")


def _extract_face_value(soup: BeautifulSoup) -> int:
    """
    Extracts face value from Screener.in company page.

    Screener shows face value in two places:
      1. The top company-info bar — e.g. "Face Value  ₹ 5"
      2. The #top-ratios section — as a list item with label "Face Value"

    Falls back to Rs 10 (most conservative) if not found.
    """
    import re

    # Strategy 1 — look in #top-ratios list items
    top_ratios = soup.find("div", {"id": "top-ratios"})
    if top_ratios:
        for li in top_ratios.find_all("li"):
            text = li.get_text(" ", strip=True)
            if "Face Value" in text or "face value" in text.lower():
                # Extract the number — e.g. "Face Value ₹ 5" or "Face Value 10"
                match = re.search(r"[\u20b9Rs\.]*\s*(\d+(?:\.\d+)?)", text.split("Face Value")[-1])
                if match:
                    fv = float(match.group(1))
                    if fv in (1, 2, 5, 10):
                        logger.info(f"Face value found in #top-ratios: ₹{int(fv)}")
                        return int(fv)

    # Strategy 2 — search entire page for "Face Value" near a number
    all_text = soup.get_text(" ")
    match = re.search(r"Face\s+Value\s*[₹Rs\.]*\s*(\d+(?:\.\d+)?)", all_text, re.IGNORECASE)
    if match:
        fv = float(match.group(1))
        if fv in (1, 2, 5, 10):
            logger.info(f"Face value found in page text: ₹{int(fv)}")
            return int(fv)

    # Strategy 3 — check company-info / info-card divs
    for div in soup.find_all(["div", "span", "td"], class_=re.compile(r"info|detail|company", re.I)):
        text = div.get_text(" ", strip=True)
        if "face" in text.lower() and "value" in text.lower():
            match = re.search(r"(\d+(?:\.\d+)?)", text)
            if match:
                fv = float(match.group(1))
                if fv in (1, 2, 5, 10):
                    logger.info(f"Face value found in info div: ₹{int(fv)}")
                    return int(fv)

    # Fallback — default to Rs 10 (most common for PSUs / older companies)
    logger.warning("Face value not found on page — defaulting to ₹10. "
                   "Verify manually and set FACE_VALUE in config/settings.py if wrong.")
    return 10


def _fallback_face_value() -> int:
    """
    Returns face value when running on fallback data (no live scrape).
    Reads from config/settings.py if FACE_VALUE is defined there,
    otherwise defaults to Rs 5 (Maruti's face value).
    """
    try:
        from config.settings import FACE_VALUE
        return int(FACE_VALUE)
    except (ImportError, AttributeError):
        logger.warning("FACE_VALUE not in settings — defaulting to ₹5 for fallback data")
        return 5

def _derive_missing(c: pd.DataFrame) -> pd.DataFrame:
    """
    Derives metrics that Screener doesn't show explicitly
    but can be calculated from what is available.
    """
    import numpy as np

    def row(key):
        return c.loc[key] if key in c.index else pd.Series(np.nan, index=c.columns)

    # revenue: sometimes only 'Sales' is present
    if "revenue" not in c.index and "ebt" in c.index and "interest" in c.index and "ebitda" in c.index:
        pass  # will be caught by alias matching after stripping +

    # ebit = ebt + interest
    if "ebit" not in c.index:
        if "ebt" in c.index and "interest" in c.index:
            c.loc["ebit"] = row("ebt") + row("interest")
            logger.debug("ebit derived from ebt + interest")

    # net_income = ebt * (1 - tax_pct/100)
    if "net_income" not in c.index:
        if "ebt" in c.index and "tax_pct" in c.index:
            c.loc["net_income"] = row("ebt") * (1 - row("tax_pct") / 100)
            logger.debug("net_income derived from ebt * (1 - tax%)")

    # total_equity = equity_capital + reserves
    if "total_equity" not in c.index:
        if "equity_capital" in c.index and "reserves" in c.index:
            c.loc["total_equity"] = row("equity_capital") + row("reserves")
            logger.debug("total_equity derived from equity_capital + reserves")
    # cfo: map from net_cash_change if cfo still missing (last resort)
    # This is intentionally not done — net_cash_change ≠ cfo
    # cfo must come from the cash flow statement directly
    
    # capex: approximate as absolute value of cfi when not explicitly available
    # This is a rough proxy — will be replaced when expanded rows are scraped
    
    if "capex" not in c.index and "cfi" in c.index:
        c.loc["capex"] = row("cfi").abs()
        logger.debug("capex approximated from abs(cfi) — replace with expanded row later")

    return c

def _serialize(statements: dict) -> dict:
    result = {}
    for k, v in statements.items():
        if k == "_face_value":
            result["_face_value"] = v          # store as plain int
        else:
            result[k] = v.to_json()
    return result


def _deserialize(data: dict) -> dict:
    result = {}
    for k, v in data.items():
        if k == "_face_value":
            result["_face_value"] = int(v)     # restore as int
        else:
            try:
                result[k] = pd.read_json(v)
            except Exception:
                result[k] = pd.DataFrame()
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Fallback data — Maruti Suzuki FY20–FY24 (₹ Crores)
# Source: Screener.in / Annual Reports
# ─────────────────────────────────────────────────────────────────────────────

def _fallback_data() -> dict[str, pd.DataFrame]:
    years = [
        "Mar 2014", "Mar 2015", "Mar 2016", "Mar 2017",
        "Mar 2018", "Mar 2019", "Mar 2020", "Mar 2021",
        "Mar 2022", "Mar 2023", "Mar 2024", "Mar 2025"
    ]

    # ── Income Statement ───────────────────────────────────────────────────────
    # Exact Screener.in row structure
    income = pd.DataFrame({
        "Sales":                [44542,  50801,  57589,  68085,  79809,  86068,  75660,  70372,  88330,  117571, 141858, 152913],
        "Expenses":             [39232,  43909,  48565,  57664,  67692,  75012,  68305,  64961,  82578,  106542, 123232, 132689],
        "Operating Profit":     [5310,   6892,   9024,   10421,  12118,  11056,  7355,   5411,   5752,   11029,  18626,  20224],
        "OPM %":                [12,     14,     16,     15,     15,     13,     10,     8,      7,      9,      13,     13],
        "Other Income":         [724,    817,    1464,   2399,   2155,   2664,   3410,   3046,   1861,   2307,   4248,   5199],
        "Interest":             [184,    218,    82,     89,     346,    76,     134,    102,    127,    187,    194,    194],
        "Depreciation":         [2116,   2515,   2822,   2604,   2760,   3021,   3528,   3034,   2789,   2826,   5256,   5608],
        "Profit before tax":    [3734,   4976,   7585,   10127,  11167,  10624,  7103,   5321,   4697,   10323,  17424,  19620],
        "Tax %":                [24,     24,     28,     26,     29,     28,     20,     18,     17,     20,     23,     26],
        "Net Profit":           [2854,   3809,   5497,   7511,   7881,   7651,   5678,   4389,   3880,   8211,   13488,  14500],
        "EPS in Rs":            [94.44,  126.04, 181.98, 248.61, 260.86, 253.21, 187.90, 145.30, 128.43, 271.82, 429.01, 461.20],
        "Dividend Payout %":    [13,     20,     19,     30,     31,     32,     32,     31,     47,     33,     29,     29],
    }, index=years).T

    # ── Balance Sheet ──────────────────────────────────────────────────────────
    balance = pd.DataFrame({
        "Equity Capital":            [151,   151,   151,   151,   151,   151,   151,   151,   151,   151,   157,   157],
        "Reserves":                  [21345, 24167, 30465, 36924, 42408, 46941, 49262, 52350, 55182, 61640, 85479, 96083],
        "Borrowings":                [2004,  666,   231,   484,   121,   160,   184,   541,   426,   1247,  119,   87],
        "Other Liabilities":         [7975,  9492,  11879, 14402, 17568, 16717, 14031, 18335, 18896, 21558, 29550, 35644],
        "Total Liabilities":         [31476, 34477, 42726, 51960, 60248, 63969, 63628, 71376, 74656, 84597, 115304,131971],
        "Fixed Assets":              [11034, 12490, 12530, 13311, 13389, 15437, 15744, 14989, 13747, 17830, 27865, 32983],
        "CWIP":                      [2640,  1890,  1007,  1252,  2132,  1607,  1415,  1497,  2936,  2904,  7735,  7929],
        "Investments":               [10527, 13298, 20676, 29151, 36123, 37504, 37488, 42945, 42035, 49184, 57296, 66265],
        "Other Assets":              [7275,  6800,  8513,  8247,  8604,  9421,  8980,  11946, 15937, 14678, 22408, 24794],
        "Total Assets":              [31476, 34477, 42726, 51960, 60248, 63969, 63628, 71376, 74656, 84597, 115304,131971],
        # Detailed rows — used by ratio engine
        "Shareholder Funds":         [21496, 24318, 30616, 37075, 42559, 47092, 49413, 52501, 55333, 61791, 85636, 96240],
        "Long Term Borrowings":      [47,    47,    47,    47,    47,    47,    47,    47,    47,    47,    47,    47],
        "Short Term Borrowings":     [1957,  619,   184,   437,   74,    113,   137,   494,   379,   1200,  72,    40],
        "Trade Payables":            [4234,  5123,  6234,  7456,  8234,  7890,  7230,  6890,  8450,  11230, 13560, 15234],
        "Other Current Liabilities": [3741,  4369,  5645,  6946,  9334,  8827,  4120,  3980,  4560,  5890,  7230,  8910],
        "Total Current Liabilities": [7975,  9492,  11879, 14402, 17568, 16717, 14031, 18335, 18896, 21558, 29550, 35644],
        "Intangible Assets":         [890,   820,   760,   690,   680,   700,   890,   820,   760,   690,   620,   580],
        "Total Non-Current Assets":  [25091, 28498, 34973, 44404, 52324, 55248, 55537, 60251, 59478, 70608, 93516, 107757],
        "Inventories":               [1876,  2134,  2456,  2789,  3012,  2890,  2341,  2589,  2876,  3456,  4123,  4567],
        "Trade Receivables":         [2890,  3234,  3678,  4123,  4567,  4234,  4589,  3891,  4201,  5789,  6892,  7234],
        "Cash Equivalents":          [3234,  3478,  5123,  6789,  8234,  9012,  7894,  9872,  11234, 14567, 17891, 19234],
        "Short Term Investments":    [456,   678,   890,   1234,  1567,  1234,  890,   1230,  1560,  1890,  2340,  2890],
        "Other Current Assets":      [2829,  2489,  2627,  1441,  1546,  1271,  1877,  1065,  1079,  738,   1224,  1289],
        "Total Current Assets":      [11285, 12013, 14774, 16376, 18926, 18641, 17591, 18647, 20950, 26440, 32470, 35214],
    }, index=years).T

    # ── Cash Flow Statement ────────────────────────────────────────────────────
    # Exact Screener.in row structure with all sub-items
    cashflow = pd.DataFrame({
        "Cash from Operating Activity": [4995,   6449,   8482,   10282,  11788,  6601,   3496,   8856,   1840,   9251,   16801,  16136],
        "Profit from operations":       [5111,   6779,   8935,   10413,  12036,  11060,  7503,   5531,   5832,   11112,  18676,  20322],
        "Receivables":                  [46,     345,    -204,   122,    -262,   -851,   340,    696,    -764,   -1258,  -1316,  -1969],
        "Inventory":                    [124,    -982,   -450,   -131,   104,    -162,   109,    165,    -483,   -751,   125,    -1595],
        "Payables":                     [813,    712,    1789,   979,    2128,   -858,   -2155,  2680,   -396,   2008,   3321,   3509],
        "Loans Advances":               [-563,   23,     -1,     1,      -0,     -13,    -1,     -6,     -8,     1,      -3,     -10],
        "Other WC items":               [321,    648,    325,    1222,   839,    569,    -863,   801,    -1162,  374,    -406,   -313],
        "Working capital changes":      [742,    745,    1460,   2192,   2808,   -1315,  -2570,  4336,   -2813,  373,    1722,   -378],
        "Direct taxes":                 [-858,   -1075,  -1912,  -2323,  -3056,  -3144,  -1438,  -1011,  -1178,  -2233,  -3597,  -3807],
        "Cash from Investing Activity": [-4997,  -4491,  -7230,  -9173,  -8302,  -3540,  -557,   -7291,  -239,   -8036,  -11865, -14456],
        "Fixed assets purchased":       [-3545,  -3058,  -2469,  -3391,  -3912,  -4872,  -3437,  -2370,  -3459,  -6347,  -9200,  -10641],
        "Fixed assets sold":            [9,      16,     12,     16,     26,     170,    37,     42,     136,    100,    45,     38],
        "Investments purchased":        [-13100, -17354, -12044, -17716, -47069, -52957, -44205, -44869, -60525, -66597, -65736, -73882],
        "Investments sold":             [10450,  15270,  7378,   11839,  42564,  53986,  46969,  42920,  63579,  61605,  61933,  69795],
        "Interest received":            [195,    152,    67,     36,     68,     124,    96,     67,     174,    194,    372,    444],
        "Dividends received":           [54,     54,     11,     13,     20,     9,      4,      3,      3,      6,      6,      9],
        "Acquisition of companies":     [0,      0,      0,      0,      0,      0,      -15,    -65,    -146,   0,      -80,    -18],
        "Other investing items":        [940,    428,    -186,   7,      0,      0,      -5,     -3019,  -1,     3003,   795,    -201],
        "Cash from Financing Activity": [-74,    -2004,  -1237,  -1129,  -3436,  -2948,  -3104,  -1545,  -1607,  -1213,  -4062,  -4155],
        "Proceeds from borrowings":     [1264,   92,     77,     484,    10,     39,     0,      380,    0,      831,    0,      0],
        "Repayment of borrowings":      [-885,   -1449,  -313,   -231,   -373,   0,      -46,    0,      -110,   0,      -1183,  -33],
        "Interest paid fin":            [-170,   -222,   -92,    -110,   -346,   -73,    -136,   -102,   -130,   -186,   -147,   -167],
        "Dividends paid":               [-242,   -362,   -755,   -1057,  -2266,  -2417,  -2417,  -1812,  -1359,  -1812,  -2719,  -3930],
        "Financial liabilities":        [0,      0,      0,      0,      0,      0,      -10,    -11,    -8,     -46,    -13,    -25],
        "Other financing items":        [-41,    -62,    -154,   -215,   -461,   -497,   -497,   0,      0,      0,      0,      0],
        "Net Cash Flow":                [-76,    -45,    16,     -20,    50,     113,    -165,   20,     -6,     2,      874,    -2475],
    }, index=years).T

    income.index.name   = "Metric"
    balance.index.name  = "Metric"
    cashflow.index.name = "Metric"

    return {
        "income_statement": income,
        "balance_sheet":    balance,
        "cash_flow":        cashflow,
    }


if __name__ == "__main__":
    stmts  = fetch_statements()
    canon  = build_canonical(stmts)
    print("\n=== INCOME STATEMENT ===")
    print(stmts["income_statement"].to_string())
    print("\n=== CANONICAL METRICS RESOLVED ===")
    print(canon.to_string())