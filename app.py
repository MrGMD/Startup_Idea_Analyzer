"""
app.py
------
Startup Idea Analyzer — Streamlit entrypoint.

Covers:
- Landing Page + guided questions (F1, F2 / FR-01, FR-02, FR-03)
- Wiring input -> ai_engine -> scoring_engine (FR-04 through FR-07)
- Results Dashboard (F11 / FR-13)
- Graceful handling of empty/invalid input and AI failures (NFR Reliability)

UI design system: an "analyst's feasibility report" look — deep ink-navy
base, one brass accent reserved for the score/decision/primary action, and
sage/ochre/rust used only where they carry meaning (score bands, risk
severity). IBM Plex Serif for judgment text, Mono for numbers, Sans for
interactive chrome. See the design plan discussed in chat for the full
rationale. This file only changes *rendering* — the data flow (form ->
StartupInput -> analyze_startup -> AnalysisOutput -> scoring) is untouched.
"""

import html as html_lib
import os

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from ai_engine import AnalysisError, analyze_startup
from schemas import BusinessModel, StartupInput, StartupStage
from scoring_engine import calculate_overall_score, interpret_score

# --- API key loading -------------------------------------------------------
# Local dev: read from .env (python-dotenv).
# Streamlit Community Cloud: secrets are set in the app's Secrets panel and
# exposed via st.secrets, not a .env file — so mirror them into os.environ
# here if they aren't already set, and ai_engine.py doesn't need to change.
load_dotenv()
try:
    for _key in ("GROQ_API_KEY", "MODEL_NAME"):
        if _key not in os.environ and _key in st.secrets:
            os.environ[_key] = st.secrets[_key]
except Exception:
    # No secrets.toml present at all (e.g. local dev using only .env) —
    # that's a normal, supported setup, not an error.
    pass

st.set_page_config(page_title="Startup Idea Analyzer", page_icon="📋", layout="centered")


# ---------------------------------------------------------------------------
# Design system (colors, type, component styles)
# ---------------------------------------------------------------------------
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
  --ink: #0B1220;
  --panel: #141B2E;
  --hairline: #26314A;
  --paper: #E8ECF4;
  --slate: #8A93A8;
  --brass: #D9A441;
  --brass-light: #E8BE6E;
  --sage: #5FA88F;
  --ochre: #C98A3E;
  --rust: #C1554A;
}

.stApp { background-color: var(--ink) !important; color: var(--paper); }
[data-testid="stHeader"] { background: rgba(0,0,0,0); }
.main .block-container { padding-top: 2.5rem; padding-bottom: 3rem; max-width: 760px; }

h1, h2, h3 {
  font-family: 'IBM Plex Serif', serif !important;
  color: var(--paper) !important;
  font-weight: 600 !important;
}

hr { border-color: var(--hairline) !important; }

/* form inputs */
.stTextInput input, .stTextArea textarea,
.stSelectbox [data-baseweb="select"] div {
  background-color: var(--panel) !important;
  border-color: var(--hairline) !important;
  color: var(--paper) !important;
  border-radius: 4px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--brass) !important;
  box-shadow: 0 0 0 1px var(--brass) !important;
}
.stTextInput label p, .stTextArea label p, .stSelectbox label p {
  font-family: 'IBM Plex Sans', sans-serif !important;
  color: var(--paper) !important;
  font-weight: 500 !important;
}

/* buttons */
.stButton button, .stFormSubmitButton button {
  background-color: var(--brass) !important;
  color: var(--ink) !important;
  border: none !important;
  border-radius: 4px !important;
  font-weight: 600 !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  padding: 0.5rem 1.5rem !important;
}
.stButton button:hover, .stFormSubmitButton button:hover {
  background-color: var(--brass-light) !important;
  color: var(--ink) !important;
}

/* form container */
div[data-testid="stForm"] {
  border: 1px solid var(--hairline) !important;
  background-color: rgba(20, 27, 46, 0.4) !important;
  border-radius: 6px !important;
  padding: 1.5rem !important;
}

/* masthead */
.masthead-tag {
  font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--slate);
  border: 1px solid var(--hairline); padding: 2px 8px; border-radius: 3px; float: right;
}
.masthead-title { font-family: 'IBM Plex Serif', serif; font-size: 34px; font-weight: 600; margin: 0; color: var(--paper); }
.masthead-tagline { font-family: 'IBM Plex Serif', serif; font-style: italic; font-size: 17px; color: var(--brass); margin: 4px 0 12px 0; }
.masthead-desc { font-family: 'IBM Plex Sans', sans-serif; font-size: 14.5px; color: var(--slate); line-height: 1.5; max-width: 62ch; }

/* score stamp */
.score-wrap { display:flex; align-items:center; gap:22px; margin: 8px 0 4px 0; flex-wrap: wrap; }
.score-stamp { display:flex; flex-direction: column; align-items:center; justify-content:center; border: 2px solid var(--brass); border-radius: 6px; padding: 14px 26px; min-width: 120px; }
.score-stamp .num { font-family:'IBM Plex Mono', monospace; font-size: 42px; font-weight:600; line-height:1; }
.score-stamp .denom { font-family:'IBM Plex Mono', monospace; font-size:12px; color:var(--slate); margin-top:2px; }
.score-band { font-family:'IBM Plex Serif', serif; font-size:19px; font-weight:600; }
.score-sub { font-family:'IBM Plex Sans', sans-serif; font-size:13px; color:var(--slate); margin-top:2px; }

/* category bars */
.cat-row { margin-bottom: 16px; }
.cat-label { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:5px; }
.cat-name { font-family:'IBM Plex Sans', sans-serif; font-size:14px; color:var(--paper); font-weight:500; }
.cat-num { font-family:'IBM Plex Mono', monospace; font-size:13px; color:var(--slate); }
.cat-track { background: var(--panel); border:1px solid var(--hairline); border-radius:3px; height:7px; overflow:hidden; }
.cat-fill { height:100%; border-radius:3px; width:0%; }
.cat-reasoning { font-family:'IBM Plex Serif', serif; font-style:italic; font-size:13px; color:var(--slate); margin-top:5px; }

/* strengths / weaknesses lists */
.list-title { font-family:'IBM Plex Sans', sans-serif; font-weight:600; font-size:14px; margin-bottom:8px; }
.list-title.sage { color: var(--sage); }
.list-title.rust { color: var(--rust); }
.plain-list { margin:0; padding-left:18px; font-family:'IBM Plex Sans', sans-serif; font-size:14px; color:var(--paper); line-height:1.6; }

/* risk cards */
.risk-card { background: var(--panel); border:1px solid var(--hairline); border-left: 4px solid var(--rust); border-radius: 4px; padding: 12px 16px; margin-bottom: 10px; }
.risk-head { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
.risk-title { font-family:'IBM Plex Sans', sans-serif; font-weight:600; font-size:14.5px; color:var(--paper); }
.risk-sev { font-family:'IBM Plex Mono', monospace; font-size:11px; padding:1px 7px; border-radius:3px; color:var(--ink); }
.risk-desc { font-family:'IBM Plex Serif', serif; font-size:14px; color:var(--paper); margin: 4px 0 8px 0; line-height:1.5; }
.risk-mit { font-family:'IBM Plex Sans', sans-serif; font-size:13px; color:var(--slate); }

/* recommendations */
.rec-row { display:flex; gap:10px; margin-bottom:10px; align-items:baseline; }
.rec-num { font-family:'IBM Plex Mono', monospace; color:var(--brass); font-weight:600; min-width:18px; }
.rec-title { font-family:'IBM Plex Sans', sans-serif; font-weight:600; color:var(--paper); font-size:14px; }
.rec-detail { font-family:'IBM Plex Sans', sans-serif; color:var(--slate); font-size:13.5px; }

/* validation plan */
.plan-row { display:flex; gap:14px; margin-bottom:8px; }
.plan-day { font-family:'IBM Plex Mono', monospace; color:var(--brass); font-size:13px; min-width:64px; }
.plan-action { font-family:'IBM Plex Sans', sans-serif; color:var(--paper); font-size:14px; }

/* decision badge */
.decision-badge { display:inline-block; font-family:'IBM Plex Mono', monospace; font-weight:600; font-size: 14px; padding:8px 18px; border-radius:4px; border:2px solid var(--brass); color: var(--brass); }

.section-divider { border: none; border-top: 1px solid var(--hairline); margin: 26px 0; }
</style>
"""


def _e(text) -> str:
    """Escape any user- or AI-generated text before inserting into raw HTML."""
    return html_lib.escape(str(text))


def _band_color(score: int) -> str:
    """Maps a 0-100 score to its semantic band color (mirrors scoring_engine.SCORE_BANDS)."""
    if score >= 80:
        return "#5FA88F"  # sage — Strong potential
    if score >= 65:
        return "#D9A441"  # brass — Promising
    if score >= 50:
        return "#C98A3E"  # ochre — Needs significant validation
    return "#C1554A"      # rust — High uncertainty


def _severity_color(severity: str) -> str:
    return {"High": "#C1554A", "Medium": "#C98A3E", "Low": "#5FA88F"}.get(severity, "#C1554A")


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def render_landing():
    st.markdown(
        """
        <div>
          <span class="masthead-tag">v1.0</span>
          <h1 class="masthead-title">Startup Idea Analyzer</h1>
          <div class="masthead-tagline">Validate Before You Build.</div>
          <div class="masthead-desc">
            Answer a few questions about your startup idea. We'll tell you what's
            strong, what's risky, and exactly what to validate before you spend
            time building it.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
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

        submitted = st.form_submit_button("Analyze My Idea")

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


def render_score_stamp(score: int, band: str):
    color = _band_color(score)
    st.markdown(
        f"""
        <div class="score-wrap">
          <div class="score-stamp" style="border-color:{color};">
            <span class="num" style="color:{color};">{score}</span>
            <span class="denom">/ 100</span>
          </div>
          <div>
            <div class="score-band" style="color:{color};">{_e(band)}</div>
            <div class="score-sub">Recomputed from the PRD's weighted category scores.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_category_bar(key: str, cat):
    label = key.replace("_", " ").title()
    score = cat.score
    color = _band_color(score)
    anim = "fill_" + key

    # Built with plain concatenation (not an f-string) so the literal CSS
    # braces in the @keyframes rule don't need escaping.
    anim_css = (
        "<style>@keyframes " + anim + " { "
        "from { width: 0%; } "
        "to { width: " + str(score) + "%; } "
        "}</style>"
    )
    st.markdown(anim_css, unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="cat-row">
          <div class="cat-label">
            <span class="cat-name">{_e(label)}</span>
            <span class="cat-num">{score}/100</span>
          </div>
          <div class="cat-track">
            <div class="cat-fill" style="background:{color}; animation: {anim} 900ms ease-out forwards;"></div>
          </div>
          <div class="cat-reasoning">{_e(cat.reasoning)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard(analysis, recomputed_score: int, startup_name: str = ""):
    """F11 — Results Dashboard."""

    band = interpret_score(recomputed_score)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    header = f"Feasibility Report — {_e(startup_name)}" if startup_name else "Feasibility Report"
    st.markdown(f'<h2 style="margin-bottom:14px;">{header}</h2>', unsafe_allow_html=True)
    render_score_stamp(recomputed_score, band)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown('<h3>Category Breakdown</h3>', unsafe_allow_html=True)
    for key, cat in analysis.category_scores.items():
        render_category_bar(key, cat)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="list-title sage">Key Strengths</div>', unsafe_allow_html=True)
        items = "".join(f"<li>{_e(s)}</li>" for s in analysis.strengths)
        st.markdown(f'<ul class="plain-list">{items}</ul>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="list-title rust">Weaknesses</div>', unsafe_allow_html=True)
        items = "".join(f"<li>{_e(w)}</li>" for w in analysis.weaknesses)
        st.markdown(f'<ul class="plain-list">{items}</ul>', unsafe_allow_html=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown('<h3>Risks</h3>', unsafe_allow_html=True)
    for r in analysis.risks:
        sev_color = _severity_color(r.severity)
        st.markdown(
            f"""
            <div class="risk-card" style="border-left-color:{sev_color};">
              <div class="risk-head">
                <span class="risk-title">{_e(r.title)}</span>
                <span class="risk-sev" style="background:{sev_color};">{_e(r.severity)}</span>
              </div>
              <div class="risk-desc">{_e(r.description)}</div>
              <div class="risk-mit"><b>Suggested mitigation:</b> {_e(r.mitigation)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown('<h3>Critical Assumptions</h3>', unsafe_allow_html=True)
    items = "".join(f"<li>{_e(a)}</li>" for a in analysis.assumptions)
    st.markdown(f'<ol class="plain-list">{items}</ol>', unsafe_allow_html=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown('<h3>Top Recommendations</h3>', unsafe_allow_html=True)
    for rec in sorted(analysis.recommendations, key=lambda r: r.priority):
        st.markdown(
            f"""
            <div class="rec-row">
              <span class="rec-num">{rec.priority}.</span>
              <div><span class="rec-title">{_e(rec.title)}</span><br>
              <span class="rec-detail">{_e(rec.detail)}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown('<h3>7-Day Validation Plan</h3>', unsafe_allow_html=True)
    for day in analysis.validation_plan.days:
        st.markdown(
            f"""
            <div class="plan-row">
              <span class="plan-day">{_e(day.day)}</span>
              <span class="plan-action">{_e(day.action)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div style="margin-top:8px;"><span class="decision-badge">Decision: {_e(analysis.validation_plan.decision)}</span></div>',
        unsafe_allow_html=True,
    )


def main():
    inject_css()
    render_landing()
    startup_input = render_guided_questions()

    # A fresh form submission runs the analysis and caches it in session_state.
    # This matters because interacting with the dashboard afterwards would
    # otherwise trigger a Streamlit rerun where the form is NOT resubmitted —
    # without caching, the whole report would vanish.
    if startup_input is not None:
        with st.spinner("Analyzing your idea..."):
            try:
                analysis = analyze_startup(startup_input)
                st.session_state["analysis"] = analysis
                st.session_state["recomputed_score"] = calculate_overall_score(analysis)
                st.session_state["startup_name"] = startup_input.startup_name
            except AnalysisError as e:
                # NFR Reliability — never crash the app on API/AI failures
                st.error(f"We couldn't complete the analysis: {e}")
                st.info("Please try again in a moment.")
                return

    if "analysis" in st.session_state:
        render_dashboard(
            st.session_state["analysis"],
            st.session_state["recomputed_score"],
            st.session_state.get("startup_name", ""),
        )


if __name__ == "__main__":
    main()
