"""
Groq LLM client wrapper — openai/gpt-oss-20b.

All LLM tasks route through this module:
  - Consent validation
  - Q1-Q8 field extraction (JSON mode)
  - Cross-field consistency check
  - SHAP plain-English reason generation
"""
import json
import logging

from groq import AsyncGroq

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncGroq(api_key=settings.groq_api_key)
        logger.info("Groq LLM client initialised (model=%s)", settings.groq_llm_model)
    return _client


async def call_json(prompt: str, schema_hint: str = "") -> dict:
    """
    Call the LLM in JSON mode. Returns parsed dict.
    Raises ValueError on JSON parse failure.
    """
    settings = get_settings()
    client = _get_client()
    full_prompt = prompt + "\n\nRespond ONLY with valid JSON. No markdown fences, no explanation."
    if schema_hint:
        full_prompt += f"\n\nExpected JSON schema:\n{schema_hint}"

    response = await client.chat.completions.create(
        model=settings.groq_llm_model,
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0,
        max_completion_tokens=2048,
    )
    text = response.choices[0].message.content.strip()

    # Strip markdown fences if the model adds them anyway
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("LLM JSON parse error: %s | raw: %s", e, text[:500])
        raise ValueError(f"LLM returned invalid JSON: {e}") from e


async def call_text(prompt: str) -> str:
    """Call the LLM for a plain text response."""
    settings = get_settings()
    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.groq_llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_completion_tokens=1024,
    )
    return response.choices[0].message.content.strip()
