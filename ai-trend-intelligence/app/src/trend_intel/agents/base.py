"""BaseAgent — JSON mode, Pydantic-validated output, corrective re-prompt + bounded retry (FR-017a, SC-012)."""
from __future__ import annotations

import json
import re
from typing import Any, Generic, TypeVar

from openai import APIError
from pydantic import BaseModel, ValidationError

from trend_intel.agents.openrouter_client import get_openrouter_client
from trend_intel.config import get_settings
from trend_intel.core.errors import AgentError
from trend_intel.core.logging import get_logger

log = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)

AGENT_ROLES = frozenset(
    {"research", "trend_analysis", "technical_analyst", "comparison", "ranking", "report_writer", "quality_reviewer"}
)

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from plain text or markdown-fenced blocks."""
    text = text.strip()
    # Try markdown fence first
    m = _FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()
    return json.loads(text)


def _coerce_to_schema(parsed: dict[str, Any], schema: type[T]) -> T:
    """
    Accept both envelope format  {"ok": true, "data": {...}}
    and flat format              {"summary": "...", ...}
    Free models often return flat JSON without the ok/data wrapper.
    """
    # Try data envelope first
    if "data" in parsed and isinstance(parsed["data"], dict):
        try:
            return schema.model_validate(parsed["data"])
        except ValidationError:
            pass
    # Try flat object directly
    return schema.model_validate(parsed)


class BaseAgent(Generic[T]):
    role: str
    system_prompt: str
    output_schema: type[T]

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = get_openrouter_client()

    def _model(self) -> str:
        return self._settings.openrouter_default_model

    async def run(self, user_content: str) -> T:
        """Call OpenRouter, validate output, bounded retry."""
        max_retries = self._settings.agent_max_retries
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 2):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model(),
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.2,
                    max_tokens=1000,
                )
                raw = response.choices[0].message.content or "{}"
                parsed = _extract_json(raw)
                result = _coerce_to_schema(parsed, self.output_schema)
                log.info("agent_success", role=self.role, attempt=attempt)
                return result

            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                log.warning("agent_schema_error", role=self.role, attempt=attempt, error=str(exc))
                if attempt <= max_retries:
                    user_content = (
                        f"{user_content}\n\n[CORRECTION] Previous response did not match the required JSON schema. "
                        f"Return ONLY a valid JSON object. Error: {exc}"
                    )
            except APIError as exc:
                last_error = exc
                log.warning("agent_api_error", role=self.role, attempt=attempt, error=str(exc))
                if attempt > max_retries:
                    break

        raise AgentError(f"Agent {self.role} failed after {max_retries + 1} attempts: {last_error}")

    async def run_safe(self, user_content: str) -> T | None:
        """Return None on failure instead of raising (per-tool isolation, FR-011)."""
        try:
            return await self.run(user_content)
        except AgentError as exc:
            log.error("agent_failed_isolated", role=self.role, error=str(exc))
            return None
