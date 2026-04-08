"""
Common-size financial statements.
  Income Statement  → every line as % of Revenue
  Balance Sheet     → every line as % of Total Assets
"""

import pandas as pd
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)


def common_size_income(income_df: pd.DataFrame) -> pd.DataFrame:
    """
    income_df: raw income statement (index=Metric, columns=years).
    Returns same shape with values as % of Revenue.
    """
    if income_df.empty:
        return pd.DataFrame()

    # Find revenue row — try multiple labels
    rev_candidates = ["Sales", "Revenue from Operations", "Net Revenue", "Total Revenue"]
    rev_row = None
    for label in rev_candidates:
        if label in income_df.index:
            rev_row = income_df.loc[label]
            break

    if rev_row is None:
        logger.warning("Revenue row not found in income statement for common-size")
        return pd.DataFrame()

    cs = income_df.div(rev_row) * 100
    cs.index.name = "Metric (% of Revenue)"
    logger.info(f"Common-size income statement: {cs.shape}")
    return cs


def common_size_balance(balance_df: pd.DataFrame) -> pd.DataFrame:
    """
    balance_df: raw balance sheet (index=Metric, columns=years).
    Returns same shape with values as % of Total Assets.
    """
    if balance_df.empty:
        return pd.DataFrame()

    asset_candidates = ["Total Assets", "Total Liabilities"]
    asset_row = None
    for label in asset_candidates:
        if label in balance_df.index:
            asset_row = balance_df.loc[label]
            break

    if asset_row is None:
        logger.warning("Total Assets row not found for common-size balance sheet")
        return pd.DataFrame()

    cs = balance_df.div(asset_row) * 100
    cs.index.name = "Metric (% of Total Assets)"
    logger.info(f"Common-size balance sheet: {cs.shape}")
    return cs