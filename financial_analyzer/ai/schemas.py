"""
Pydantic schemas for structured AI output.
Claude returns JSON — these models validate and parse it.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class CategoryCommentary(BaseModel):
    category: str = Field(description="Ratio category name")
    headline: str = Field(description="One-line summary of the category")
    commentary: str = Field(description="2-3 sentence analytical commentary")
    trend: str = Field(description="improving / stable / deteriorating")


class RedFlag(BaseModel):
    metric: str = Field(description="Ratio or metric name")
    value: str = Field(description="Actual value that triggered the flag")
    severity: str = Field(description="high / medium / low")
    explanation: str = Field(description="Why this is a concern")


class InvestmentThesis(BaseModel):
    company: str
    overall_rating: str = Field(description="Strong / Adequate / Weak")
    key_strengths: List[str] = Field(description="Top 3 financial strengths")
    key_concerns: List[str] = Field(description="Top 3 financial concerns")
    executive_summary: str = Field(description="3-4 sentence investment thesis")


class RedFlagReport(BaseModel):
    company: str
    total_flags: int
    flags: List[RedFlag]
    overall_risk: str = Field(description="Low / Medium / High")
    risk_summary: str = Field(description="2 sentence risk summary")


class FullCommentaryReport(BaseModel):
    company: str
    categories: List[CategoryCommentary]
    thesis: InvestmentThesis
    red_flags: RedFlagReport