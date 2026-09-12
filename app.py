"""
app.py
------
Startup Idea Analyzer — Streamlit entrypoint.

Covers:
- Landing Page + guided questions (F1, F2 / FR-01, FR-02, FR-03)
- Wiring input -> ai_engine -> scoring_engine (FR-04 through FR-07)
- Results Dashboard (F11 / FR-13)
- Graceful handling of empty/invalid input and AI failures (NFR Reliability)
"""

import os

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from schemas import StartupInput, BusinessModel, StartupStage
from ai_engine import analyze_startup, AnalysisError
from scoring_engine import calculate_overall_score, interpret_score, score_color

# --- API key loading -------------------------------------------------------
# Local dev: read from .env (python-dotenv).
# Streamlit Community Cloud: secrets are set in the app's Secrets panel and
# exposed via st.secrets, not a .env file — so mirror them into os.environ
# here if they aren't already set, and ai_engine.py doesn't need to change.
load_dotenv()
for _key in ("GROQ_API_KEY", "MODEL_NAME"):
    if _key not in os.environ and _key in st.secrets:
        os.environ[_key] = st.secrets[_key]

st.set_page_config(page_title="Startup Idea Analyzer", page_icon="🚀", layout="centered")


def render_landing():
    st.title("🚀 Startup Idea Analyzer")
    st.subheader("Validate Before You Build.")
    st.write(
        "Answer a few questions about your startup idea. We'll tell you what's strong, "
        "what's risky, and exactly what to validate before you spend time building it."
    )


def render_guided_questions() -> StartupInput | None:
    """F2 — Guided Questions (Q1-Q8). Returns a validated StartupInput or None."""

    with st.form("startup_form"):
        startup_name = st.text_input("Startup Name", placeholder="e.g. SkillBridge")
        idea = st.text_area("Q1. What is your startup idea?", placeholder="Describe it in a sentence or two.")
        problem = st.text_area("Q2. What problem are you solving?")
        target_customer = st.text_input("Q3. Who is your target customer?")
        solution = st.text_area("Q4. How does your solution solve the problem?")
        current_alternatives = st.text_area(
            "Q5. How do customers currently solve this problem? (optional)", value=""
        )
        business_model = st.selectbox(
            "Q6. How will your startup make money?",
            options=[b.value for b in BusinessModel],
        )
        market = st.text_input("Q7. Where do you plan to launch?", placeholder="e.g. Pakistan")
        stage = st.selectbox(
            "Q8. What stage are you currently at?",
            options=[s.value for s in StartupStage],
        )

        submitted = st.form_submit_button("Analyze My Idea →")

    if not submitted:
        return None

    # FR-03 — validate required fields before sending to the AI engine
    try:
        return StartupInput(
            startup_name=startup_name,
            idea=idea,
            problem=problem,
            target_customer=target_customer,
            solution=solution,
            current_alternatives=current_alternatives or None,
            business_model=BusinessModel(business_model),
            market=market,
            stage=StartupStage(stage),
        )
    except ValidationError as e:
        st.error("Please fill in all required fields with a bit more detail:")
        for err in e.errors():
            field = err["loc"][0] if err["loc"] else "field"
            st.write(f"- **{field}**: {err['msg']}")
        return None


def render_dashboard(analysis, recomputed_score: int):
    """F11 — Results Dashboard."""

    band = interpret_score(recomputed_score)
    color = score_color(recomputed_score)

    st.divider()
    st.markdown(f"## Overall Score: **{recomputed_score}/100**")
    st.markdown(f":{color}[**{band.upper()}**]")

    st.divider()
    st.markdown("### Category Breakdown")
    for key, cat in analysis.category_scores.items():
        st.write(f"**{key.replace('_', ' ').title()}**: {cat.score}/100")
        st.progress(cat.score / 100)
        st.caption(cat.reasoning)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💪 Key Strengths")
        for s in analysis.strengths:
            st.write(f"- {s}")
    with col2:
        st.markdown("### ⚠️ Weaknesses")
        for w in analysis.weaknesses:
            st.write(f"- {w}")

    st.divider()
    st.markdown("### 🚨 Risks")
    for r in analysis.risks:
        with st.expander(f"{r.title} — {r.severity} severity"):
            st.write(r.description)
            st.write(f"**Suggested mitigation:** {r.mitigation}")

    st.divider()
    st.markdown("### 🧩 Critical Assumptions")
    for i, a in enumerate(analysis.assumptions, start=1):
        st.write(f"{i}. {a}")

    st.divider()
    st.markdown("### 🔥 Top Recommendations")
    for rec in sorted(analysis.recommendations, key=lambda r: r.priority):
        st.write(f"**{rec.priority}. {rec.title}** — {rec.detail}")

    st.divider()
    st.markdown("### 🧪 7-Day Validation Plan")
    for day in analysis.validation_plan.days:
        st.write(f"**{day.day}:** {day.action}")
    st.markdown(f"**Decision: `{analysis.validation_plan.decision}`**")


def main():
    render_landing()
    startup_input = render_guided_questions()

    if startup_input is None:
        return

    with st.spinner("Analyzing your idea..."):
        try:
            analysis = analyze_startup(startup_input)
            recomputed_score = calculate_overall_score(analysis)
        except AnalysisError as e:
            # NFR Reliability — never crash the app on API/AI failures
            st.error(f"We couldn't complete the analysis: {e}")
            st.info("Please try again in a moment.")
            return

    render_dashboard(analysis, recomputed_score)


if __name__ == "__main__":
    main()
