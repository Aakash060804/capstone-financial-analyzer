"""
Parses raw HTML tables from Screener.in into clean DataFrames.
Handles expanded sub-rows, percentage rows, and blank separators.
"""

import re
import pandas as pd
from bs4 import BeautifulSoup, Tag
from utils.logger import get_logger

logger = get_logger(__name__)


def _clean_number(text: str) -> float | None:
    """Convert '1,23,456.78' or '12%' or '-' to float. Returns None if unparseable."""
    text = text.strip().replace(",", "").replace("%", "").replace("−", "-")
    if text in ("", "-", "--", "N/A", "na", "NA"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _extract_years(thead: Tag) -> list[str]:
    """Extract year labels from the table header row."""
    years = []
    for th in thead.find_all("th"):
        text = th.get_text(strip=True)
        # Keep only year-like headers: 'Mar 2024', 'TTM', 'FY24', '2024'
        if re.search(r"(Mar|Sep|Dec|Jun|FY|20\d{2}|TTM)", text):
            years.append(text)
    return years


def _get_row_meta(tr: Tag) -> dict:
    """
    Extract metadata from a table row:
        - label       : the metric name (first cell text)
        - row_id      : data-ttm-id or id attribute (used for parent-child linking)
        - parent_id   : data-child-of attribute (marks sub-rows)
        - is_separator: True if row is a visual separator with no data
    """
    cells = tr.find_all(["td", "th"])
    if not cells:
        return None

    label_cell = cells[0]
    label = label_cell.get_text(strip=True).rstrip("+").strip()

    row_id    = tr.get("id", "") or tr.get("data-ttm-id", "")
    parent_id = tr.get("data-child-of", "")

    is_separator = (
        not label
        or label.startswith("---")
        or tr.get("class") and "sub" in " ".join(tr.get("class", []))
    )

    return {
        "label":        label,
        "row_id":       row_id,
        "parent_id":    parent_id,
        "is_separator": is_separator,
        "cells":        cells,
    }


def parse_screener_table(section: Tag, years: list[str] | None = None) -> pd.DataFrame:
    """
    Parse one Screener.in section (profit-loss / balance-sheet / cash-flow).

    Returns a DataFrame with:
        - Index  : metric label (string)
        - Columns: year labels (string)
        - Values : float or NaN

    Sub-rows (expandable items) are included with their original label.
    Parent rows that are pure totals are also kept.
    """
    table = section.find("table")
    if not table:
        logger.warning("No <table> found in section")
        return pd.DataFrame()

    thead = table.find("thead")
    tbody = table.find("tbody")
    if not thead or not tbody:
        logger.warning("Missing thead or tbody")
        return pd.DataFrame()

    if years is None:
        years = _extract_years(thead)

    if not years:
        logger.warning("Could not extract year headers")
        return pd.DataFrame()

    logger.debug(f"Years found: {years}")

    rows_data = {}

    for tr in tbody.find_all("tr", recursive=False):
        meta = _get_row_meta(tr)
        if not meta:
            continue
        if meta["is_separator"] and not meta["label"]:
            continue

        label = meta["label"]
        if not label:
            continue

        # Avoid overwriting a parent row with a sub-row of the same name
        if label in rows_data:
            label = f"{label} (detail)"

        cells = meta["cells"]
        values = {}
        for i, yr in enumerate(years):
            cell_idx = i + 1  # offset by 1 because cells[0] is the label
            if cell_idx < len(cells):
                val = _clean_number(cells[cell_idx].get_text(strip=True))
                values[yr] = val
            else:
                values[yr] = None

        rows_data[label] = values
        logger.debug(f"  Row parsed: {label} → {values}")

    if not rows_data:
        return pd.DataFrame()

    df = pd.DataFrame(rows_data).T
    df.index.name = "Metric"

    # Convert all to numeric properly
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info(f"Parsed table: {df.shape[0]} rows x {df.shape[1]} years")
    return df