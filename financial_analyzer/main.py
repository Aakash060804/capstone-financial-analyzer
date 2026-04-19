"""
Main pipeline orchestrator.

Usage:
    python main.py                        # default company (settings.py)
    python main.py --company INFY         # Switch company
    python main.py --no-ai                # Skip AI (no API key needed)
    python main.py --no-cache             # Force fresh data fetch
    python main.py --no-forecast          # Skip forecasting
"""

import os
import sys
import time
import argparse
from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Financial Analysis Pipeline")
    parser.add_argument("--company",     type=str,  help="Screener.in slug (INFY, TCS, RELIANCE)")
    parser.add_argument("--no-ai",       action="store_true")
    parser.add_argument("--no-cache",    action="store_true")
    parser.add_argument("--no-forecast", action="store_true")
    parser.add_argument("--fast",        action="store_true",
                        help="Skip Prophet + anomaly detection. Targets ~30s total.")
    return parser.parse_args()


def override_company(slug: str):
    import config.settings as cfg
    cfg.SCREENER_SLUG   = slug.upper()
    cfg.SCREENER_URL    = f"{cfg.SCREENER_BASE}/company/{cfg.SCREENER_SLUG}/consolidated/"
    cfg.OUTPUT_FILENAME = f"{cfg.SCREENER_SLUG}_Financial_Analysis.xlsx"
    cfg.COMPANY_NAME    = slug.upper()


def main():
    args = parse_args()
    if args.company:
        override_company(args.company)

    from config.settings         import COMPANY_NAME, OUTPUT_DIR, OUTPUT_FILENAME
    from extraction.scraper      import fetch_statements, build_canonical
    from extraction.validator    import validate
    from engine.ratios           import compute_all
    from engine.dupont           import compute_dupont
    from engine.common_size      import common_size_income, common_size_balance
    from engine.schedules        import working_capital_schedule, debt_schedule
    from ai.chains               import run_ai_analysis
    from forecasting.scenarios   import build_scenarios
    from forecasting.dcf         import run_dcf
    from forecasting.sensitivity import build_sensitivity_table
    from excel.builder           import build_workbook

    print("\n" + "═" * 65)
    print(f"  FINANCIAL ANALYSIS PIPELINE")
    print(f"  Company : {COMPANY_NAME}")
    print(f"  Output  : {os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)}")
    print("═" * 65 + "\n")

    t_start = time.time()

    # ── 1. Data Ingestion ──────────────────────────────────────────────────────
    print("[1/7] Fetching financial statements...")
    stmts = fetch_statements(use_cache=not args.no_cache)

    # ── 2. Canonicalize ────────────────────────────────────────────────────────
    print("[2/7] Building canonical data frame...")
    canon    = build_canonical(stmts)
    warnings = validate(canon)
    if warnings:
        for w in warnings:
            print(f"       ⚠  {w}")

    # ── 2.5 Anomaly Detection ──────────────────────────────────────────────────
    print("[2.5/7] Running anomaly detection...")
    anomaly_report = {"flags": [], "summary": {
        "metrics_scanned": 0, "years_scanned": 0,
        "total_flags": 0, "errors": 0, "warnings": 0,
        "info_count": 0, "integrity_score": 100.0,
    }}
    if args.fast:
        print("       Skipped (--fast mode)")
    else:
        try:
            from extraction.anomaly_detector import run_anomaly_detection
            anomaly_report = run_anomaly_detection(canon)
            s = anomaly_report["summary"]
            print(f"       Scan complete — {s['total_flags']} flags · integrity: {s['integrity_score']}%")
        except Exception as e:
            print(f"       Anomaly detection failed: {e} — continuing pipeline")
    # ──────────────────────────────────────────────────────────────────────────

    # ── 3. Engine ──────────────────────────────────────────────────────────────
    print("[3/7] Computing ratios, DuPont, schedules...")
    ratios   = compute_all(canon)
    dupont   = compute_dupont(canon)
    wc_sched = working_capital_schedule(canon)
    dt_sched = debt_schedule(canon)
    cs_inc   = common_size_income(stmts["income_statement"])
    cs_bal   = common_size_balance(stmts["balance_sheet"])

    # ── 3.5 Industry Classification ───────────────────────────────────────────
    # Classifies company into sector using Euclidean distance on 8 key ratios.
    # Assigns peer group and peer median benchmarks used in cover sheet,
    # ratios sheet, AI commentary, and audit trail.
    print("[3.5/7] Running industry classification...")
    clustering_result = None
    try:
        from engine.industry_clustering import classify_sector
        clustering_result = classify_sector(ratios)
        cr = clustering_result
        print(f"       Sector: {cr['sector']} (confidence: {cr['confidence']*100:.0f}%)")
        print(f"       Peers: {', '.join(cr['peers'][:4])}")
    except Exception as e:
        print(f"       Industry classification failed: {e} — using defaults")
    # ──────────────────────────────────────────────────────────────────────────

    # ── 4. AI Commentary ───────────────────────────────────────────────────────
    print("[4/7] Generating AI commentary...")
    if args.no_ai:
        print("       Skipped (--no-ai)")
        from ai.chains import FinancialAnalysisChains
        report = FinancialAnalysisChains()._rule_based_fallback(COMPANY_NAME, ratios)
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        report  = run_ai_analysis(COMPANY_NAME, ratios, api_key=api_key)

    # ── 5. Forecasting ─────────────────────────────────────────────────────────
    print("[5/7] Building scenario forecasts...")
    if args.no_forecast:
        print("       Skipped (--no-forecast)")
        scenarios      = {}
        dcf_result     = None
        sensitivity    = None
        prophet_result = {"available": False}
    else:
        face_value = stmts.get("_face_value", 10)
        print(f"       Face value: ₹{face_value} (auto-detected from Screener)")

        scenarios  = build_scenarios(canon)

        # ── Prophet Time Series Forecasting ───────────────────────────────────
        print("[5.5/7] Running Prophet time series forecast...")
        prophet_result = {"available": False}
        if args.fast:
            print("       Skipped (--fast mode) — Prophet can take 2-5 min, not suitable for web")
        else:
            try:
                import signal as _signal

                def _timeout_handler(signum, frame):
                    raise TimeoutError("Prophet exceeded 90s limit")

                _signal.signal(_signal.SIGALRM, _timeout_handler)
                _signal.alarm(90)   # hard 90-second limit per Prophet run
                try:
                    from forecasting.prophet_forecast import run_prophet_forecast
                    from config.settings import FORECAST_YEARS as FY
                    prophet_result = run_prophet_forecast(canon, forecast_years=FY)
                    if prophet_result.get("available"):
                        print(f"       Prophet complete — Revenue/EBITDA/FCF models trained")
                    else:
                        print("       Prophet not available")
                finally:
                    _signal.alarm(0)  # cancel alarm
            except (TimeoutError, Exception) as e:
                print(f"       Prophet skipped: {e} — continuing pipeline")
        # ──────────────────────────────────────────────────────────────────────

        # ── Dynamic WACC ───────────────────────────────────────────────────────
        print("[2.7/7] Computing dynamic WACC...")
        wacc_result = None
        dynamic_wacc = None
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
            from forecasting.wacc_calculator import compute_wacc
            from config.settings import SCREENER_SLUG
            wacc_timeout = 15 if args.fast else 45
            with ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(compute_wacc, canon, SCREENER_SLUG)
                wacc_result  = fut.result(timeout=wacc_timeout)
                dynamic_wacc = wacc_result["wacc"]
            print(f"       WACC: {dynamic_wacc*100:.2f}% · Beta: {wacc_result['beta']:.2f} ({wacc_result['beta_source']})")
        except (FutureTimeout, Exception) as e:
            print(f"       Dynamic WACC skipped ({type(e).__name__}) — using settings default")
        # ──────────────────────────────────────────────────────────────────────

        dcf_result = run_dcf(canon, face_value=face_value, wacc=dynamic_wacc)

        # ── Monte Carlo DCF ────────────────────────────────────────────────────
        from forecasting.monte_carlo import run_monte_carlo
        dcf_result["monte_carlo"] = run_monte_carlo(dcf_result, canon)
        mc = dcf_result["monte_carlo"]
        print(
            f"       Monte Carlo complete — "
            f"p25: {mc['label_p25']} | "
            f"median: {mc['label_p50']} | "
            f"p75: {mc['label_p75']}"
        )
        # ──────────────────────────────────────────────────────────────────────

        sensitivity = build_sensitivity_table(dcf_result)

    # ── 6. Excel ───────────────────────────────────────────────────────────────
    print("[6/7] Building Excel workbook...")
    out_path = build_workbook(
        statements     = stmts,
        canon_df       = canon,
        ratio_df       = ratios,
        dupont_df      = dupont,
        wc_schedule    = wc_sched,
        debt_schedule  = dt_sched,
        report         = report,
        scenarios      = scenarios,
        dcf_result     = dcf_result or {},
        sensitivity_df = sensitivity if sensitivity is not None
                        else __import__("pandas").DataFrame(),
        anomaly_report    = anomaly_report,
        wacc_result       = wacc_result,
        prophet_result    = prophet_result if not args.no_forecast else {"available": False},
        clustering_result = clustering_result,
    )

    # ── 7. JSON Export ────────────────────────────────────────────────────────
    print("[7/7] Exporting full analysis to JSON...")
    try:
        from utils.json_exporter import export_to_json
        from config.settings import SCREENER_SLUG
        json_path = export_to_json(
            output_dir        = OUTPUT_DIR,
            company_slug      = SCREENER_SLUG,
            company_name      = COMPANY_NAME,
            statements        = stmts,
            canon_df          = canon,
            ratio_df          = ratios,
            dupont_df         = dupont,
            cs_inc            = cs_inc,
            cs_bal            = cs_bal,
            wc_schedule       = wc_sched,
            debt_schedule     = dt_sched,
            report            = report,
            scenarios         = scenarios,
            dcf_result        = dcf_result or {},
            sensitivity_df    = sensitivity if sensitivity is not None
                                else __import__("pandas").DataFrame(),
            anomaly_report    = anomaly_report,
            wacc_result       = wacc_result if not args.no_forecast else None,
            prophet_result    = prophet_result if not args.no_forecast else {"available": False},
            clustering_result = clustering_result,
        )
        print(f"       JSON saved → {json_path}")
    except Exception as e:
        print(f"       JSON export failed: {e}")
    # ──────────────────────────────────────────────────────────────────────────

    elapsed = time.time() - t_start
    print(f"\n{'═'*65}")
    print(f"  ✅  Complete in {elapsed:.1f}s")
    print(f"  📁  {out_path}")
    print(f"{'═'*65}\n")


if __name__ == "__main__":
    main()