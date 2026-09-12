"""
schemas.py
----------
Structured/validated output — Section 23 (AI Output Structure) and FR-02/FR-08.

Two model groups:
1. StartupInput   — what the user provides via the guided questions (F1/F2)
2. AnalysisOutput — the structured JSON the AI must return (never raw prose)

Using Pydantic means malformed AI output (NFR Reliability: "Unexpected AI output")
fails validation immediately instead of silently breaking the dashboard.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Input side — Section 9/10 (F1 — Startup Idea Input, F2 — Guided Questions)
# ---------------------------------------------------------------------------

class BusinessModel(str, Enum):
    SUBSCRIPTION = "Subscription"
    COMMISSION = "Commission"
    ADVERTISING = "Advertising"
    FREEMIUM = "Freemium"
    ONE_TIME_PAYMENT = "One-time payment"
    B2B = "B2B"
    OTHER = "Other"


class StartupStage(str, Enum):
    IDEA = "Idea"
    RESEARCH = "Research"
    PROTOTYPE = "Prototype"
    MVP = "MVP"
    EARLY_USERS = "Early users"
    REVENUE = "Revenue"


class StartupInput(BaseModel):
    """Everything collected from Q1-Q8 in the guided questions flow."""

    startup_name: str = Field(..., min_length=1, max_length=120)
    idea: str = Field(..., min_length=15, description="Q1 — What is your startup idea?")
    problem: str = Field(..., min_length=10, description="Q2 — What problem are you solving?")
    target_customer: str = Field(..., min_length=5, description="Q3 — Who is your target customer?")
    solution: str = Field(..., min_length=10, description="Q4 — How does your solution solve the problem?")
    current_alternatives: Optional[str] = Field(
        default=None, description="Q5 — How do customers currently solve this problem?"
    )
    business_model: BusinessModel = Field(..., description="Q6")
    market: str = Field(..., min_length=2, description="Q7 — Where do you plan to launch?")
    stage: StartupStage = Field(..., description="Q8 — What stage are you currently at?")

    @field_validator("idea", "problem", "solution")
    @classmethod
    def not_just_whitespace(cls, v: str) -> str:
        # NFR Reliability — guard against "Very short ideas" / empty-looking input
        if not v.strip():
            raise ValueError("This field cannot be empty or whitespace only.")
        return v.strip()


# ---------------------------------------------------------------------------
# Output side — Section 23 (AI Output Structure) + F5-F10
# ---------------------------------------------------------------------------

class CategoryScore(BaseModel):
    """One of the 8 analysis dimensions (Section 11 / F3)."""

    score: int = Field(..., ge=0, le=100)
    reasoning: str = Field(..., min_length=1, description="Why this score — NFR Explainability")
    confidence: float = Field(..., ge=0.0, le=1.0)


class Risk(BaseModel):
    """F7 — Risk Analysis. Specific, not generic."""

    title: str
    description: str
    severity: str = Field(..., pattern="^(Low|Medium|High)$")
    mitigation: str


class ValidationDay(BaseModel):
    """One day inside the F9 7-Day Validation Plan."""

    day: str  # e.g. "Day 1" or "Day 2-3"
    action: str


class ValidationPlan(BaseModel):
    days: List[ValidationDay]
    decision: str = Field(..., pattern="^(BUILD|MODIFY|VALIDATE MORE)$")


class Recommendation(BaseModel):
    """F10 — Top Recommendations, prioritized."""

    title: str
    detail: str
    priority: int = Field(..., ge=1)


class AnalysisOutput(BaseModel):
    """
    The full Feasibility Report contract (Section 23).
    ai_engine.py must produce JSON that validates against this model
    before it ever reaches the dashboard.
    """

    overall_score: int = Field(..., ge=0, le=100)
    assessment: str = Field(..., description="Human-readable summary, e.g. 'Promising — validate key assumptions'")

    category_scores: dict[str, CategoryScore] = Field(
        ..., description="Keys: problem_strength, customer_clarity, market_opportunity, "
                          "competition, differentiation, business_model, feasibility, risk"
    )

    strengths: List[str]
    weaknesses: List[str]
    risks: List[Risk]
    assumptions: List[str]
    recommendations: List[Recommendation]
    validation_plan: ValidationPlan

    class Config:
        extra = "forbid"  # reject unexpected keys from the LLM rather than silently ignoring them
