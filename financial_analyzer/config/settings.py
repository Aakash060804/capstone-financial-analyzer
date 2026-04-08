"""
Central config. To analyze a different company:
    1. Change COMPANY_NAME and SCREENER_SLUG
    2. Run main.py — everything else adapts automatically
"""

# ── Company ────────────────────────────────────────────────────────────────────
COMPANY_NAME  = "Reliance Industries Ltd"
SCREENER_SLUG = "RELIANCE"
SCREENER_BASE = "https://www.screener.in"
SCREENER_URL  = f"{SCREENER_BASE}/company/{SCREENER_SLUG}/consolidated/"

# ── Output ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR      = "outputs"
OUTPUT_FILENAME = f"{SCREENER_SLUG}_Financial_Analysis.xlsx"

# ── LLM ────────────────────────────────────────────────────────────────────────
LLM_MODEL      = "claude-sonnet-4-20250514"
LLM_MAX_TOKENS = 2000
LLM_TEMPERATURE = 0.3

# ── Forecasting ────────────────────────────────────────────────────────────────
FORECAST_YEARS = 5
SCENARIO_ASSUMPTIONS = {
    "base": {"revenue_growth": 0.10, "ebit_margin_delta":  0.00, "tax_rate": 0.25},
    "bull": {"revenue_growth": 0.15, "ebit_margin_delta":  0.02, "tax_rate": 0.25},
    "bear": {"revenue_growth": 0.05, "ebit_margin_delta": -0.02, "tax_rate": 0.25},
}

# ── DCF ────────────────────────────────────────────────────────────────────────
DCF_WACC            = 0.14   # fallback only — overridden by dynamic WACC
DCF_TERMINAL_GROWTH = 0.04
DCF_PROJECTION_YEARS = 5

# ── Dynamic WACC (CAPM) ────────────────────────────────────────────────────
RISK_FREE_RATE      = 0.068  # 10-yr Indian G-Sec yield — update quarterly
EQUITY_RISK_PREMIUM = 0.055  # Standard India ERP
MARKET_RETURN       = 0.120  # Nifty 50 long-run average

# ── Scraper ────────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 20
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Canonical metric map ────────────────────────────────────────────────────────
# Keys   = internal names used by engine/, excel/, ai/
# Values = list of possible labels from Screener.in (checked in order)
CANONICAL_MAP = {

    # ── Income Statement ───────────────────────────────────────────────────
    "revenue":              ["Sales", "Revenue from Operations",
                            "Net Revenue", "Total Revenue"],
    "total_expenses":       ["Expenses", "Total Expenses",
                            "Total Operating Expenses"],
    "other_income":         ["Other Income", "Non-Operating Income"],
    "ebitda":               ["Operating Profit", "EBITDA", "PBDIT"],
    "opm_pct":              ["OPM %", "Operating Profit Margin %"],
    "depreciation":         ["Depreciation", "Depreciation & Amortisation Expenses",
                            "D&A"],
    "ebit":                 ["EBIT", "Operating Profit after Depreciation"],
    "interest":             ["Interest", "Finance Costs", "Interest Expense"],
    "ebt":                  ["EBT", "Profit before tax", "PBT",
                            "Profit Before Tax"],
    "tax":                  ["Tax", "Income Tax", "Tax Expense"],
    "tax_pct":              ["Tax %"],
    "net_income":           ["Net Profit", "Profit after Tax", "PAT",
                            "Net Income", "Profit for the Year"],
    "eps":                  ["EPS in Rs", "Basic EPS", "EPS"],
    "dividend_payout":      ["Dividend Payout %", "Dividend %"],

    # ── Balance Sheet ──────────────────────────────────────────────────────
    "equity_capital":       ["Equity Capital", "Share Capital"],
    "reserves":             ["Reserves", "Reserves & Surplus"],
    "total_equity":         ["Shareholder Funds", "Total Shareholder's Equity",
                            "Net Worth", "Total Equity"],
    "total_borrowings":     ["Borrowings", "Total Debt", "Total Borrowings"],
    "other_liabilities":    ["Other Liabilities"],
    "total_liabilities":    ["Total Liabilities", "Total Equity & Liabilities"],
    "fixed_assets":         ["Fixed Assets", "Net Block",
                            "Property, Plant & Equipment"],
    "cwip":                 ["CWIP", "Capital Work in Progress"],
    "investments":          ["Investments", "Long Term Investments"],
    "total_assets":         ["Total Assets"],
    "inventories":          ["Inventories", "Inventory", "Stock"],
    "receivables":          ["Trade Receivables", "Debtors",
                            "Accounts Receivable"],
    "cash":                 ["Cash Equivalents", "Cash & Bank Balances",
                            "Cash and Cash Equivalents"],
    "total_current_assets": ["Total Current Assets", "Current Assets"],
    "total_current_liab":   ["Total Current Liabilities", "Current Liabilities"],
    "inventories":          ["Inventories", "Inventory", "Stock",
                            "Inventories (2)"],
    "receivables":          ["Trade Receivables", "Debtors",
                            "Accounts Receivable", "Sundry Debtors"],
    "cash":                 ["Cash Equivalents", "Cash & Bank Balances",
                            "Cash and Cash Equivalents",
                            "Cash & Cash Equivalents"],
    "total_current_assets": ["Total Current Assets", "Current Assets",
                            "Other Assets"],
    "total_current_liab":   ["Total Current Liabilities",
                            "Current Liabilities", "Other Liabilities"],
    "trade_payables":       ["Trade Payables", "Creditors",
                            "Accounts Payable", "Sundry Creditors"],

    # ── Cash Flow ──────────────────────────────────────────────────────────
    "cfo": [
        "Cash from Operating Activity",
        "Net Cash from Operating Activities",
        "Net Cash Generated from Operating Activities",
    ],
    "cfi":                  ["Cash from Investing Activity",
                            "Net Cash from Investing Activities"],
    "cff":                  ["Cash from Financing Activity",
                            "Net Cash from Financing Activities"],
    "capex": [
        "Fixed assets purchased",
        "Capital Expenditure",
        "Purchase of Fixed Assets",
        "Purchase of Property, Plant & Equipment",
        "Additions to Fixed Assets",
    ],
    "net_cash_change":      ["Net Cash Flow", "Net Change in Cash"],
}

# ── Ratio red flag thresholds ──────────────────────────────────────────────────
RED_FLAG_THRESHOLDS = {
    "current_ratio_min":     1.0,
    "quick_ratio_min":       0.75,
    "interest_coverage_min": 3.0,
    "debt_equity_max":       2.0,
    "fcf_margin_min":        0.0,
    "roce_min":              10.0,
}

# ── Peer companies (for comparison sheet) ─────────────────────────────────────
PEER_SLUGS = ["M&M", "TATAMOTORS", "HEROMOTOCO", "BAJAJ-AUTO"]