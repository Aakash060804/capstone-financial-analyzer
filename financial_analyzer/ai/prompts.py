"""
All prompt templates for the AI chains.
Kept separate so prompts can be tuned without touching chain logic.
"""

from langchain_core.prompts import ChatPromptTemplate

# ── System persona ─────────────────────────────────────────────────────────────
ANALYST_SYSTEM = """You are a senior equity research analyst at a top-tier Indian investment bank. 
You write concise, professional, data-driven commentary based strictly on the financial ratios provided.

Rules you must follow:
- Never fabricate or modify any numerical values
- Base every observation strictly on the numbers given
- Use professional equity research language
- Be specific — reference actual numbers in your commentary
- Do not give investment advice or buy/sell recommendations
- Return only valid JSON matching the requested schema exactly"""


# ── Category commentary prompt ─────────────────────────────────────────────────
CATEGORY_COMMENTARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", ANALYST_SYSTEM),
    ("human", """Analyze the following {category} ratios for {company} and return a JSON object.

Ratios ({years}):
{ratio_data}

Return this exact JSON structure:
{{
    "category": "{category}",
    "headline": "one line summary",
    "commentary": "2-3 sentences of analytical commentary referencing specific numbers",
    "trend": "improving or stable or deteriorating"
}}

Return only the JSON object, no other text.""")
])


# ── Investment thesis synthesis prompt ─────────────────────────────────────────
SYNTHESIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", ANALYST_SYSTEM),
    ("human", """Based on the following category-level commentaries for {company}, 
synthesize an overall investment thesis.

Category Commentaries:
{all_commentaries}

Most Recent Year Key Metrics:
{key_metrics}

Return this exact JSON structure:
{{
    "company": "{company}",
    "overall_rating": "Strong or Adequate or Weak",
    "key_strengths": ["strength 1", "strength 2", "strength 3"],
    "key_concerns": ["concern 1", "concern 2", "concern 3"],
    "executive_summary": "3-4 sentence investment thesis paragraph"
}}

Return only the JSON object, no other text.""")
])


# ── Red flag detection prompt ──────────────────────────────────────────────────
RED_FLAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", ANALYST_SYSTEM),
    ("human", """Scan the following financial ratios for {company} and identify red flags.

All Ratios (most recent 3 years):
{ratio_data}

Thresholds to check against:
{thresholds}

A red flag is triggered when:
- A ratio breaches its threshold
- A ratio shows consistent deterioration over 3 years
- A ratio is significantly worse than typical industry norms

Return this exact JSON structure:
{{
    "company": "{company}",
    "total_flags": <number>,
    "flags": [
        {{
            "metric": "ratio name",
            "value": "actual value",
            "severity": "high or medium or low",
            "explanation": "specific explanation of the concern"
        }}
    ],
    "overall_risk": "Low or Medium or High",
    "risk_summary": "2 sentence summary of overall risk profile"
}}

Return only the JSON object, no other text.""")
])