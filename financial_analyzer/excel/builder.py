"""
Master workbook orchestrator.
Calls all sheet builders in order and saves the file.
"""

import os
from openpyxl import Workbook
from config.settings import OUTPUT_DIR, OUTPUT_FILENAME
from excel.sheets.cover       import build_cover_sheet
from excel.sheets.statements  import (
    build_income_statement, build_balance_sheet, build_cash_flow
)
from excel.sheets.ratios      import build_ratios_sheet
from excel.sheets.dupont      import build_dupont_sheet
from excel.sheets.commentary  import build_commentary_sheet
from excel.sheets.forecasts   import build_forecasts_sheet
from excel.sheets.audit       import build_audit_sheet
from utils.logger             import get_logger

logger = get_logger(__name__)


def build_workbook(
    statements:     dict,
    canon_df,
    ratio_df,
    dupont_df,
    wc_schedule,
    debt_schedule,
    report,
    scenarios:      dict,
    dcf_result:     dict,
    sensitivity_df,
    anomaly_report: dict = None,
    wacc_result:    dict = None,
    prophet_result:    dict = None,
    clustering_result: dict = None,
) -> str:
    """
    Assembles the full workbook and saves to outputs/.
    Returns the absolute file path.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

    wb = Workbook()

    logger.info("Building workbook sheets...")

    build_cover_sheet(wb, ratio_df, report, clustering_result=clustering_result)
    build_income_statement(wb, statements["income_statement"])
    build_balance_sheet(wb,    statements["balance_sheet"])
    build_cash_flow(wb,        statements["cash_flow"])
    build_ratios_sheet(wb,     ratio_df, clustering_result=clustering_result)
    build_dupont_sheet(wb,     dupont_df)
    build_commentary_sheet(wb, report)
    build_forecasts_sheet(wb,  scenarios, dcf_result, sensitivity_df,
                            prophet_result=prophet_result)
    build_audit_sheet(
        wb,
        canon_shape    = canon_df.shape,
        ratio_shape    = ratio_df.shape,
        anomaly_report    = anomaly_report,
        wacc_result       = wacc_result,
        clustering_result = clustering_result,
    )

    wb.save(out_path)
    logger.info(f"Workbook saved → {out_path}")
    return os.path.abspath(out_path)