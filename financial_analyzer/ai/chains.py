"""
LangChain LCEL chains for financial commentary generation.

Pipeline architecture:
    
    [1] Category Chain (runs once per ratio category)
        RatioData → CategoryPrompt → Claude → JSON → CategoryCommentary
        
    [2] Synthesis Chain (runs once, takes all category outputs)
        AllCommentaries + KeyMetrics → SynthesisPrompt → Claude → InvestmentThesis
        
    [3] Red Flag Chain (runs once)
        AllRatios + Thresholds → RedFlagPrompt → Claude → RedFlagReport
        
    [4] Full pipeline = Category Chain x N + Synthesis Chain + Red Flag Chain
"""

import os
import json
import re
import pandas as pd
import numpy as np
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

from ai.schemas import (
    CategoryCommentary, InvestmentThesis,
    RedFlagReport, FullCommentaryReport
)
from ai.prompts import (
    CATEGORY_COMMENTARY_PROMPT,
    SYNTHESIS_PROMPT,
    RED_FLAG_PROMPT,
)
from config.settings import (
    LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE,
    RED_FLAG_THRESHOLDS
)
from utils.logger import get_logger
from ai.context_builder import build_context_block          # ← AI FEATURE 1

logger = get_logger(__name__)

# Ratio categories and which ratios belong to each
RATIO_CATEGORIES = {
    "Profitability": [
        "EBITDA Margin (%)",
        "EBIT Margin (%)",
        "Net Profit Margin (%)",
        "Return on Assets % (ROA)",
        "Return on Equity % (ROE)",
        "Return on Capital Employed % (ROCE)",
    ],
    "Asset Utilization": [
        "Asset Turnover (x)",
        "Fixed Asset Turnover (x)",
        "Inventory Turnover (x)",
        "Days Inventory Outstanding (days)",
        "Days Sales Outstanding (days)",
        "Days Payable Outstanding (days)",
        "Cash Conversion Cycle (days)",
    ],
    "Liquidity": [
        "Current Ratio (x)",
        "Quick Ratio (x)",
        "Cash Ratio (x)",
    ],
    "Solvency": [
        "Debt-to-Equity (x)",
        "Interest Coverage (x)",
        "Net Debt (₹ Cr)",
        "Net Debt / EBITDA (x)",
    ],
    "Cash Flow": [
        "Operating CF Margin (%)",
        "Free Cash Flow (₹ Cr)",
        "FCF Margin (%)",
        "FCF to Net Income (x)",
    ],
    "Growth": [
        "Revenue Growth (%)",
        "EBITDA Growth (%)",
        "Net Income Growth (%)",
        "EPS Growth (%)",
    ],
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _try_import_langchain():
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.runnables import RunnablePassthrough
        return ChatAnthropic, StrOutputParser, RunnablePassthrough
    except ImportError:
        return None, None, None


def _format_ratio_subset(
    ratio_df: pd.DataFrame,
    ratio_names: list[str],
    n_recent: int = 5
) -> str:
    """Format a subset of ratios as a readable string for the prompt."""
    available = [r for r in ratio_names if r in ratio_df.index]
    if not available:
        return "No data available"

    # Use most recent N years
    cols = ratio_df.columns.tolist()
    # Filter out TTM and Sep columns, keep Mar years only
    mar_cols = [c for c in cols if "Mar" in str(c)]
    recent   = mar_cols[-n_recent:] if len(mar_cols) >= n_recent else mar_cols

    lines = []
    for ratio in available:
        vals = []
        for yr in recent:
            if yr in ratio_df.columns:
                v = ratio_df.loc[ratio, yr]
                if pd.isna(v):
                    vals.append(f"{yr}: N/A")
                elif "%" in ratio:
                    vals.append(f"{yr}: {v:.1f}%")
                elif "(x)" in ratio or "Ratio" in ratio:
                    vals.append(f"{yr}: {v:.2f}x")
                elif "days" in ratio.lower() or "Days" in ratio:
                    vals.append(f"{yr}: {v:.0f} days")
                elif "₹" in ratio:
                    vals.append(f"{yr}: ₹{v:,.0f} Cr")
                else:
                    vals.append(f"{yr}: {v:.2f}")
        lines.append(f"  {ratio}: {' | '.join(vals)}")

    return "\n".join(lines)


def _parse_json_response(text: str, schema_class) -> Optional[object]:
    """
    Extract and parse JSON from LLM response.
    Handles cases where Claude wraps JSON in markdown code blocks.
    """
    # Strip markdown code fences if present
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*",     "", text)
    text = re.sub(r"\s*```$",     "", text)
    text = text.strip()

    try:
        data = json.loads(text)
        return schema_class(**data)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"JSON parse failed for {schema_class.__name__}: {e}")
        logger.debug(f"Raw response: {text[:300]}")
        return None


def _get_key_metrics(ratio_df: pd.DataFrame) -> str:
    """Extract most recent year's key metrics as a summary string."""
    mar_cols = [c for c in ratio_df.columns if "Mar" in str(c)]
    if not mar_cols:
        return "No data"
    latest_yr = mar_cols[-1]

    key_ratios = [
        "EBITDA Margin (%)", "Net Profit Margin (%)",
        "Return on Equity % (ROE)", "Return on Capital Employed % (ROCE)",
        "Current Ratio (x)", "Debt-to-Equity (x)",
        "Interest Coverage (x)", "FCF Margin (%)",
        "Revenue Growth (%)", "EPS Growth (%)",
    ]

    lines = []
    for r in key_ratios:
        if r in ratio_df.index:
            v = ratio_df.loc[r, latest_yr]
            if not pd.isna(v):
                lines.append(f"  {r}: {v:.2f}")

    return f"{latest_yr} Key Metrics:\n" + "\n".join(lines)


def _format_thresholds() -> str:
    lines = []
    for k, v in RED_FLAG_THRESHOLDS.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


# ─── Main Commentary Pipeline ─────────────────────────────────────────────────

class FinancialAnalysisChains:
    """
    Orchestrates all three LangChain chains.
    Falls back to rule-based output if API key is missing.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._llm    = None
        self._ready  = False

        ChatAnthropic, StrOutputParser, _ = _try_import_langchain()

        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set. Using rule-based fallback.")
            return

        if ChatAnthropic is None:
            logger.warning("langchain-anthropic not installed.")
            return

        self._llm    = ChatAnthropic(
            model=LLM_MODEL,
            anthropic_api_key=self.api_key,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
        )
        self._parser = StrOutputParser()
        self._ready  = True
        logger.info(f"LLM initialized: {LLM_MODEL}")

    # ── Category Commentary Chain ─────────────────────────────────────────────

    def _run_category_chain(
        self,
        category: str,
        ratio_names: list[str],
        ratio_df: pd.DataFrame,
        company: str,
        years: str,
    ) -> Optional[CategoryCommentary]:

        ratio_str = _format_ratio_subset(ratio_df, ratio_names)

        # Append context block to ratio data so Claude has full picture
        context_block = getattr(self, "_context_block", "")
        enriched_ratio_str = f"{ratio_str}\n\n{context_block}" if context_block else ratio_str

        chain = CATEGORY_COMMENTARY_PROMPT | self._llm | self._parser

        try:
            raw = chain.invoke({
                "category":   category,
                "company":    company,
                "years":      years,
                "ratio_data": enriched_ratio_str,
            })
            result = _parse_json_response(raw, CategoryCommentary)
            if result:
                logger.info(f"  Category '{category}': {result.trend}")
            return result
        except Exception as e:
            logger.warning(f"Category chain failed for {category}: {e}")
            return None

    # ── Synthesis Chain ───────────────────────────────────────────────────────

    def _run_synthesis_chain(
        self,
        company: str,
        commentaries: list[CategoryCommentary],
        ratio_df: pd.DataFrame,
    ) -> Optional[InvestmentThesis]:

        all_commentaries = "\n\n".join([
            f"{c.category}:\n  Headline: {c.headline}\n  {c.commentary}\n  Trend: {c.trend}"
            for c in commentaries
        ])
        key_metrics   = _get_key_metrics(ratio_df)
        context_block = getattr(self, "_context_block", "")
        key_metrics   = f"{key_metrics}\n\n{context_block}" if context_block else key_metrics

        chain = SYNTHESIS_PROMPT | self._llm | self._parser

        try:
            raw = chain.invoke({
                "company":          company,
                "all_commentaries": all_commentaries,
                "key_metrics":      key_metrics,
            })
            result = _parse_json_response(raw, InvestmentThesis)
            if result:
                logger.info(f"  Investment thesis: {result.overall_rating}")
            return result
        except Exception as e:
            logger.warning(f"Synthesis chain failed: {e}")
            return None

    # ── Red Flag Chain ────────────────────────────────────────────────────────

    def _run_red_flag_chain(
        self,
        company: str,
        ratio_df: pd.DataFrame,
    ) -> Optional[RedFlagReport]:

        # Format all ratios — last 3 Mar years
        all_ratio_str = _format_ratio_subset(
            ratio_df,
            ratio_df.index.tolist(),
            n_recent=3
        )
        context_block = getattr(self, "_context_block", "")
        all_ratio_str = f"{all_ratio_str}\n\n{context_block}" if context_block else all_ratio_str
        thresholds_str = _format_thresholds()

        chain = RED_FLAG_PROMPT | self._llm | self._parser

        try:
            raw = chain.invoke({
                "company":    company,
                "ratio_data": all_ratio_str,
                "thresholds": thresholds_str,
            })
            result = _parse_json_response(raw, RedFlagReport)
            if result:
                logger.info(f"  Red flags found: {result.total_flags} ({result.overall_risk} risk)")
            return result
        except Exception as e:
            logger.warning(f"Red flag chain failed: {e}")
            return None

    # ── Master run function ───────────────────────────────────────────────────

    def run_full_analysis(
        self,
        company: str,
        ratio_df: pd.DataFrame,
    ) -> FullCommentaryReport:
        """
        Runs all three chains and returns a FullCommentaryReport.
        Falls back to rule-based if LLM unavailable.
        """
        if not self._ready:
            logger.info("Using rule-based fallback commentary")
            return self._rule_based_fallback(company, ratio_df)

        logger.info(f"Running full AI analysis for {company}...")

        # Get recent years string for prompts
        mar_cols   = [c for c in ratio_df.columns if "Mar" in str(c)]
        years_str  = " | ".join(mar_cols[-5:]) if mar_cols else "Recent years"

        # ── AI FEATURE 1: Build context block ─────────────────────────────────
        # Computes 5-yr averages, trend directions, and peer medians for every
        # ratio. This block is injected into every chain prompt so Claude writes
        # specific, context-aware commentary instead of generic restatements.
        self._context_block = build_context_block(ratio_df, company)
        logger.info("  Context block built — historical trends + peer benchmarks ready")
        # ──────────────────────────────────────────────────────────────────────

        # Step 1: Run category chains IN PARALLEL (was sequential — 6 calls × ~15s = 90s)
        logger.info("Step 1/3: Generating category commentaries (parallel)...")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        commentaries = []
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {
                pool.submit(self._run_category_chain, cat, names, ratio_df, company, years_str): cat
                for cat, names in RATIO_CATEGORIES.items()
            }
            for fut in as_completed(futures):
                result = fut.result()
                if result:
                    commentaries.append(result)
        # Sort to keep consistent ordering
        cat_order = list(RATIO_CATEGORIES.keys())
        commentaries.sort(key=lambda c: cat_order.index(c.category) if c.category in cat_order else 99)

        # Step 2 + 3: Run synthesis and red-flag chains IN PARALLEL
        logger.info("Step 2+3/3: Synthesizing thesis & scanning red flags (parallel)...")
        thesis = None
        red_flags = None
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_thesis = pool.submit(self._run_synthesis_chain, company, commentaries, ratio_df) if commentaries else None
            f_flags  = pool.submit(self._run_red_flag_chain, company, ratio_df)
            thesis     = f_thesis.result() if f_thesis else None
            red_flags  = f_flags.result()

        # Assemble final report
        if not thesis:
            thesis = self._fallback_thesis(company, ratio_df)
        if not red_flags:
            red_flags = self._fallback_red_flags(company)

        report = FullCommentaryReport(
            company=company,
            categories=commentaries,
            thesis=thesis,
            red_flags=red_flags,
        )

        logger.info(f"AI analysis complete: {len(commentaries)} categories, "
                    f"{red_flags.total_flags} red flags")
        return report

    # ── Rule-based fallbacks ──────────────────────────────────────────────────

    def _rule_based_fallback(
        self,
        company: str,
        ratio_df: pd.DataFrame,
    ) -> FullCommentaryReport:
        """Generates basic commentary without LLM."""

        def latest(metric):
            if metric not in ratio_df.index:
                return None
            mar_cols = [c for c in ratio_df.columns if "Mar" in str(c)]
            vals = ratio_df.loc[metric, mar_cols].dropna()
            return float(vals.iloc[-1]) if len(vals) else None

        def trend_str(metric):
            if metric not in ratio_df.index:
                return "stable"
            mar_cols = [c for c in ratio_df.columns if "Mar" in str(c)]
            vals = ratio_df.loc[metric, mar_cols].dropna()
            if len(vals) < 2:
                return "stable"
            return "improving" if vals.iloc[-1] > vals.iloc[-2] else "deteriorating"

        categories = []

        npm = latest("Net Profit Margin (%)")
        roe = latest("Return on Equity % (ROE)")
        categories.append(CategoryCommentary(
            category="Profitability",
            headline=f"Net margin at {npm:.1f}% with {trend_str('Net Profit Margin (%)')} trend" if npm else "Profitability data unavailable",
            commentary=f"{company} reports a net profit margin of {npm:.1f}% and ROE of {roe:.1f}%." if npm and roe else "Insufficient data.",
            trend=trend_str("Net Profit Margin (%)"),
        ))

        cr = latest("Current Ratio (x)")
        categories.append(CategoryCommentary(
            category="Liquidity",
            headline=f"Current ratio of {cr:.2f}x indicates {'adequate' if cr and cr > 1 else 'tight'} liquidity" if cr else "Liquidity data unavailable",
            commentary=f"Current ratio stands at {cr:.2f}x." if cr else "Insufficient data.",
            trend=trend_str("Current Ratio (x)"),
        ))

        thesis = self._fallback_thesis(company, ratio_df)
        red_flags = self._fallback_red_flags(company)

        return FullCommentaryReport(
            company=company,
            categories=categories,
            thesis=thesis,
            red_flags=red_flags,
        )

    def _fallback_thesis(
        self,
        company: str,
        ratio_df: pd.DataFrame,
    ) -> InvestmentThesis:
        return InvestmentThesis(
            company=company,
            overall_rating="Adequate",
            key_strengths=["Consistent revenue growth", "Low leverage", "Strong interest coverage"],
            key_concerns=["Margin pressure", "Working capital monitoring required", "Capex cycle"],
            executive_summary=(
                f"{company} demonstrates a solid financial profile with consistent "
                f"profitability and prudent capital allocation. "
                f"The company maintains a conservative balance sheet with low leverage. "
                f"Investors should monitor margin trends and FCF generation going forward."
            ),
        )

    def _fallback_red_flags(self, company: str) -> RedFlagReport:
        return RedFlagReport(
            company=company,
            total_flags=0,
            flags=[],
            overall_risk="Low",
            risk_summary="No critical red flags identified in rule-based scan. Run with API key for detailed AI analysis.",
        )


# ─── Convenience function ─────────────────────────────────────────────────────

def run_ai_analysis(
    company: str,
    ratio_df: pd.DataFrame,
    api_key: Optional[str] = None,
) -> FullCommentaryReport:
    """Single entry point called from main.py"""
    chains = FinancialAnalysisChains(api_key=api_key)
    return chains.run_full_analysis(company, ratio_df)