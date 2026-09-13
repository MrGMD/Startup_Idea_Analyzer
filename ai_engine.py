"""
ai_engine.py
------------
AI analysis (calling half) + Error handling — Section 11 (F3), FR-04/FR-05,
and NFR Reliability ("API failures", "Invalid responses", "Unexpected AI output").

Uses Groq's OpenAI-compatible API to run openai/gpt-oss-20b — an open-weight
model, so this can run on Groq's free tier. Reads the API key from the
environment (.env locally, Streamlit secrets when deployed) — never hardcode it.

Important: gpt-oss-20b is a REASONING model. It spends tokens "thinking"
before writing the final answer, and those thinking tokens count against
max_completion_tokens. If the budget is too small (or reasoning_effort is
too high), the model can burn its entire budget on reasoning and return an
empty or truncated response. This module detects that (finish_reason ==
"length") and retries with a larger budget instead of trying to parse
broken JSON.
"""

import os
import time
from typing import Optional

import groq
from groq import Groq
from pydantic import ValidationError

from schemas import StartupInput, AnalysisOutput
from prompts import SYSTEM_PROMPT, build_user_prompt
import json

MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-20b")
# gpt-oss supports low/medium/high. "medium" is Groq's own documented default —
# "high" reliably ate the whole token budget on thinking for this task.
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "medium")
# Starting output budget. The 8-category JSON report alone runs ~1200-1600
# tokens, plus reasoning tokens on top — 8000 gives real headroom.
INITIAL_MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8000"))
MAX_TOKENS_CEILING = 16000
MAX_RETRIES = 2


class AnalysisError(Exception):
    """Raised when the analysis could not be produced, with a user-facing message."""


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # NFR Security: fail loudly and clearly rather than leaking a stack trace
        raise AnalysisError(
            "No API key found. Set GROQ_API_KEY in your .env file (see .env.example). "
            "Get a free key at https://console.groq.com/keys"
        )
    return Groq(api_key=api_key)


def _extract_json(raw_text: str) -> dict:
    """
    LLMs sometimes wrap JSON in markdown fences despite instructions not to.
    Strip those defensively before parsing.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AnalysisError(f"AI returned output that wasn't valid JSON: {e}") from e


def analyze_startup(startup: StartupInput) -> AnalysisOutput:
    """
    Sends the structured startup input to the AI Analysis Engine (Groq /
    openai/gpt-oss-20b) and returns a validated AnalysisOutput. Raises
    AnalysisError on any failure so app.py can show a graceful message
    instead of crashing (NFR Reliability).
    """

    client = _get_client()
    user_prompt = build_user_prompt(startup)

    last_error: Optional[str] = None
    token_budget = INITIAL_MAX_TOKENS

    for attempt in range(1, MAX_RETRIES + 2):  # 1 initial try + MAX_RETRIES retries
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.6,
                max_completion_tokens=token_budget,
                reasoning_effort=REASONING_EFFORT,
            )

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            raw_text = choice.message.content or ""

            # The model ran out of budget before finishing — usually because
            # reasoning tokens consumed most or all of it. Don't try to parse
            # a half-written JSON string; retry with a bigger budget instead.
            if finish_reason == "length":
                last_error = (
                    f"response was cut off before finishing at a {token_budget}-token "
                    f"budget (likely spent on internal reasoning)"
                )
                if attempt <= MAX_RETRIES:
                    token_budget = min(int(token_budget * 1.75), MAX_TOKENS_CEILING)
                    continue
                raise AnalysisError(
                    f"The AI kept running out of its response budget after "
                    f"{MAX_RETRIES + 1} attempts (last: {last_error}). Try lowering "
                    f"REASONING_EFFORT to 'low' or raising MAX_TOKENS in your .env."
                )

            if not raw_text.strip():
                raise AnalysisError("AI returned an empty response.")

            data = _extract_json(raw_text)

            try:
                return AnalysisOutput.model_validate(data)
            except ValidationError as ve:
                raise AnalysisError(
                    f"AI output didn't match the expected report structure: {ve}"
                ) from ve

        except groq.RateLimitError as e:
            # Free-tier per-minute limit hit — worth a short backoff and retry
            last_error = str(e)
            if attempt <= MAX_RETRIES:
                time.sleep(3)
                continue
            raise AnalysisError(
                "Groq's free-tier rate limit was hit. Please wait a moment and try again."
            ) from e

        except (groq.APIConnectionError, groq.APITimeoutError) as e:
            last_error = str(e)
            if attempt <= MAX_RETRIES:
                continue

        except groq.APIStatusError as e:
            # non-transient error (bad request, auth, etc.) — don't retry blindly
            raise AnalysisError(f"The AI service returned an error: {e}") from e

        except AnalysisError as e:
            last_error = str(e)
            if attempt <= MAX_RETRIES:
                continue
            raise

    raise AnalysisError(
        f"Could not complete the analysis after {MAX_RETRIES + 1} attempts: {last_error}"
    )
