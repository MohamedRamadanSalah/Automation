"""BaseAgent — JSON mode, Pydantic-validated output, corrective re-prompt + bounded retry (FR-017a, SC-012)."""
from __future__ import annotations

import json
from typing import Any, Generic, TypeVar

from openai import APIError
from pydantic import BaseModel, ValidationError

from trend_intel.agents.openrouter_client import get_openrouter_client
from trend_intel.config import get_settings
from trend_intel.core.errors import AgentError
from trend_intel.core.logging import get_logger
from trend_intel.core.retry import bounded_retry

log = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)

AGENT_ROLES = frozenset(
    {"research", "trend_analysis", "technical_analyst", "comparison", "ranking", "report_writer", "quality_reviewer"}
)


class AgentResponse(BaseModel, Generic[T]):
    ok: bool
    data: T | None = None
    notes: str | None = None


class BaseAgent(Generic[T]):
    role: str
    system_prompt: str
    output_schema: type[T]

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = get_openrouter_client()

    def _model(self) -> str:
        # TODO: resolve per-role override from agent_configs table (T065)
        return self._settings.openrouter_default_model

    async def run(self, user_content: str) -> T:
        """Call OpenRouter with JSON-mode, validate output, bounded retry."""
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
                )
                raw = response.choices[0].message.content or "{}"
                parsed = json.loads(raw)
                envelope = AgentResponse[self.output_schema].model_validate(
                    {**parsed, "data": parsed.get("data", parsed)}
                )
                if not envelope.ok or envelope.data is None:
                    raise AgentError(f"Agent {self.role} self-reported failure: {envelope.notes}")
                return envelope.data
            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                log.warning("agent_schema_error", role=self.role, attempt=attempt, error=str(exc))
                if attempt <= max_retries:
                    user_content = (
                        f"{user_content}\n\n[CORRECTION REQUIRED] Previous response was invalid JSON or did not match the expected schema. "
                        f"Return ONLY a valid JSON object matching the schema. Error: {exc}"
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
