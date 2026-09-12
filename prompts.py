"""
prompts.py
----------
AI analysis — prompt half (paired with ai_engine.py for the API-calling half).

Kept in its own file on purpose: during a hackathon you'll be tweaking wording
constantly to fix bad AI outputs, and you don't want that churn mixed into
request/error-handling code.
"""

from schemas import StartupInput

# The 8 analysis dimensions — Section 11 (F3 — AI Analysis Engine)
CATEGORY_KEYS = [
    "problem_strength",
    "customer_clarity",
    "market_opportunity",
    "competition",
    "differentiation",
    "business_model",
    "feasibility",
    "risk",
]

SYSTEM_PROMPT = """You are a critical, evidence-driven startup analyst. Your job is NOT to \
predict whether a startup will succeed and NOT to be encouraging for its own sake. Your job \
is to evaluate the quality and strength of the assumptions behind the idea, exactly the way \
an experienced startup mentor would before a founder spends months building something.

You must:
- Be specific, not generic. Never say things like "competition may exist" without naming \
what kind of competition.
- Identify concrete, falsifiable assumptions the founder is implicitly making.
- Recommend the fastest, cheapest way to validate each risky assumption.
- Score honestly. A polished idea with no real differentiation should NOT score high on \
Differentiation just because it sounds nice.
- Return ONLY valid JSON matching the schema you are given. No prose before or after. No \
markdown code fences.
"""

OUTPUT_SCHEMA_INSTRUCTIONS = """
Return a single JSON object with EXACTLY these top-level keys:

{
  "overall_score": <int 0-100>,
  "assessment": "<one short phrase, e.g. 'Promising — validate key assumptions'>",
  "category_scores": {
    "problem_strength": {"score": <0-100>, "reasoning": "<why>", "confidence": <0.0-1.0>},
    "customer_clarity": {...same shape...},
    "market_opportunity": {...same shape...},
    "competition": {...same shape...},
    "differentiation": {...same shape...},
    "business_model": {...same shape...},
    "feasibility": {...same shape...},
    "risk": {...same shape...}
  },
  "strengths": ["<short bullet>", "..."],
  "weaknesses": ["<short bullet>", "..."],
  "risks": [
    {"title": "<short name>", "description": "<what could go wrong>",
     "severity": "Low|Medium|High", "mitigation": "<concrete next step>"}
  ],
  "assumptions": ["<critical assumption that must be true>", "..."],
  "recommendations": [
    {"title": "<short name>", "detail": "<concrete action>", "priority": <int, 1 = highest>}
  ],
  "validation_plan": {
    "days": [
      {"day": "Day 1", "action": "<what to do>"},
      {"day": "Day 2-3", "action": "<what to do>"},
      {"day": "Day 4", "action": "<what to do>"},
      {"day": "Day 5", "action": "<what to do>"},
      {"day": "Day 6", "action": "<what to do>"},
      {"day": "Day 7", "action": "<what to do>"}
    ],
    "decision": "BUILD|MODIFY|VALIDATE MORE"
  }
}

Do not include any keys other than the ones above. Do not wrap the JSON in markdown fences.
"""


def build_user_prompt(startup: StartupInput) -> str:
    """Turns the structured StartupInput into the analysis request sent to the LLM."""

    return f"""Analyze the following startup idea.

Startup Name: {startup.startup_name}
Idea: {startup.idea}
Problem being solved: {startup.problem}
Target customer: {startup.target_customer}
Proposed solution: {startup.solution}
Current alternatives customers use today: {startup.current_alternatives or "Not specified"}
Business model: {startup.business_model.value}
Target market / launch location: {startup.market}
Current stage: {startup.stage.value}

{OUTPUT_SCHEMA_INSTRUCTIONS}
"""
