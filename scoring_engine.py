"""
scoring_engine.py
-----------------
F4 — Scoring System (Section 12).

The AI already returns a per-category score (0-100). This module is the
deterministic layer on top: it applies the PRD's fixed weights to compute
the overall score, so the "overall_score" the AI guesses doesn't have to be
trusted blindly — you can recompute and cross-check it, or use this as the
source of truth and treat the AI's own overall_score as just a suggestion.
"""

from schemas import AnalysisOutput

# Section 12 — Initial weighting
WEIGHTS = {
    "problem_strength": 0.20,
    "customer_clarity": 0.15,
    "market_opportunity": 0.15,
    "competition": 0.10,
    "differentiation": 0.15,
    "business_model": 0.10,
    "feasibility": 0.10,
    "risk": 0.05,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Category weights must sum to 100%"


# Section 12 — Score interpretation
SCORE_BANDS = [
    (80, 100, "Strong potential"),
    (65, 79, "Promising — validate key assumptions"),
    (50, 64, "Needs significant validation"),
    (0, 49, "High uncertainty"),
]


def calculate_overall_score(analysis: AnalysisOutput) -> int:
    """Recomputes the overall score from category scores using the fixed PRD weights."""

    missing = set(WEIGHTS) - set(analysis.category_scores)
    if missing:
        raise ValueError(f"Missing category scores required for weighting: {missing}")

    weighted_sum = sum(
        analysis.category_scores[category].score * weight
        for category, weight in WEIGHTS.items()
    )
    return round(weighted_sum)


def interpret_score(score: int) -> str:
    """Maps a 0-100 overall score to its PRD interpretation band."""

    for low, high, label in SCORE_BANDS:
        if low <= score <= high:
            return label
    raise ValueError(f"Score {score} is out of the expected 0-100 range.")


def score_color(score: int) -> str:
    """Simple helper for dashboard styling — not in the PRD, but harmless UI sugar."""

    if score >= 80:
        return "green"
    if score >= 65:
        return "orange"
    if score >= 50:
        return "orange"
    return "red"
