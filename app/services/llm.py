import os
import logging
from pathlib import Path

from google import genai
from google.genai import types

from app.models import AnalysisPayload, AnalysisResult

logger = logging.getLogger(__name__)


def analyze_with_llm(email: dict) -> AnalysisResult | None:
    """Return None when live AI is unavailable, allowing a dependable local fallback."""
    if os.getenv("USE_LLM", "true").lower() == "false" or not os.getenv("GEMINI_API_KEY"):
        return None
    try:
        prompt = Path(__file__).parents[1].joinpath("prompts", "triage_prompt.txt").read_text(encoding="utf-8")
        client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY"),
            http_options=types.HttpOptions(timeout=15000),
        )
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents=f"{prompt}\n\nEMAIL TO ANALYZE:\n{email['combined']}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnalysisPayload,
                temperature=0.2,
                max_output_tokens=1200,
            ),
        )
        data = AnalysisPayload.model_validate_json(response.text or "{}")
        return AnalysisResult(**data.model_dump(), source="Gemini")
    except Exception as exc:
        logger.warning("Gemini analysis unavailable; using local fallback (%s)", type(exc).__name__)
        return None
