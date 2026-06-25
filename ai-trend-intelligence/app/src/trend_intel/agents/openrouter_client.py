"""OpenAI SDK client pointed at OpenRouter (R7)."""
from __future__ import annotations

from openai import AsyncOpenAI

from trend_intel.config import get_settings

_client: AsyncOpenAI | None = None


def get_openrouter_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            max_retries=0,  # our BaseAgent handles retries; SDK default sleeps on Retry-After which can stall for hours
        )
    return _client
