# Startup Idea Analyzer

**Validate Before You Build.**

An AI-powered Streamlit app that takes a startup idea through a guided
questionnaire and returns a structured Feasibility Report: category scores,
strengths, weaknesses, risks, critical assumptions, prioritized
recommendations, and a 7-day validation plan.

## Project structure

```
app.py               UI: landing page, guided questions, results dashboard
ai_engine.py          Calls the LLM API, validates/handles errors
prompts.py            Prompt templates (kept separate for fast iteration)
schemas.py            Pydantic models — the structured input/output contract
scoring_engine.py     Weighted scoring across the 8 PRD categories
requirements.txt
.env.example          Copy to .env and fill in your real API key
```

## Setup

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Get a free Groq API key at https://console.groq.com/keys, then copy the
   env template and add it:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env`:
   ```
   GROQ_API_KEY=gsk_...
   MODEL_NAME=openai/gpt-oss-20b
   ```
   **Never commit `.env`** — it's already in `.gitignore`.

3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Notes for the team

- The AI's output is strictly validated against `schemas.py` (`AnalysisOutput`).
  If the model returns something malformed, `ai_engine.py` raises a clean
  `AnalysisError` that `app.py` shows as a friendly message — the app should
  never crash mid-demo on bad AI output.
- Category weights and score bands live in `scoring_engine.py` — adjust them
  there if the analysis feels miscalibrated.
- Prompt wording lives entirely in `prompts.py` — iterate there without
  touching API-calling logic in `ai_engine.py`.
- Deploying: push to GitHub, then deploy on Streamlit Community Cloud (or any
  Streamlit-compatible host). Set `GROQ_API_KEY` and `MODEL_NAME` as
  secrets in the deployment settings — do not rely on a committed `.env`.
- Model: `openai/gpt-oss-20b`, an open-weight model served via Groq's
  OpenAI-compatible API. Groq's free tier has per-minute/per-day request
  limits — `ai_engine.py` retries once on a 429 with a short backoff, but if
  you're demoing to a room, consider adding a few dollars of Groq credit to
  raise those limits ahead of time.

## Out of scope for this MVP (see PRD Section 7 — Non-Goals)

No success/failure guarantees, no legal or investment advice, no company
registration, no full financial forecasting, and no replacement for real
customer interviews.
