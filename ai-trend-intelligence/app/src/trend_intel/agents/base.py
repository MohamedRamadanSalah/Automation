"""BaseAgent — JSON mode, Pydantic-validated output, corrective re-prompt + bounded retry (FR-017a, SC-012)."""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Generic, TypeVar

from openai import APIError, RateLimitError
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
    max_tokens: int = 1000  # override per agent for larger outputs

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = get_openrouter_client()

    def _model(self) -> str:
        return self._settings.openrouter_default_model

    # OpenRouter rejects a "models" fallback array longer than this.
    MAX_FALLBACK_CHAIN = 3

    def _extra_body(self) -> dict[str, Any]:
        """OpenRouter fallback routing: on 429/error, roll to the next free model."""
        fallbacks = self._settings.fallback_model_list
        if not fallbacks:
            return {}
        # Primary first, then the ordered free fallbacks (dedup, preserve order).
        chain = [self._model(), *fallbacks]
        seen: set[str] = set()
        ordered = [m for m in chain if not (m in seen or seen.add(m))]
        # OpenRouter caps the array at 3 entries; a longer list is a hard 400.
        return {"models": ordered[: self.MAX_FALLBACK_CHAIN]}

    async def run(self, user_content: str) -> T:
        """Call OpenRouter, validate output, bounded retry with backoff on rate limits."""
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
                    max_tokens=self.max_tokens,
                    extra_body=self._extra_body(),
                )
                if not response.choices:
                    raise AgentError(f"Agent {self.role} received empty choices from API")
                raw = response.choices[0].message.content or "{}"
                if not raw.strip():
                    raise AgentError(f"Agent {self.role} received empty content from API")
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
            except RateLimitError as exc:
                last_error = exc
                if "per-day" in str(exc):
                    # Account-wide daily free quota, not a per-model/per-minute limit —
                    # every model in the fallback chain shares it, so retrying (or trying
                    # another free model) cannot succeed again until the daily reset.
                    # Fail immediately instead of burning more of tomorrow's... today's
                    # already-exhausted quota on retries that are guaranteed to repeat.
                    log.warning("agent_daily_quota_exhausted", role=self.role, attempt=attempt, error=str(exc))
                    break
                # Transient per-minute rate limit. Back off (bounded) before retry
                # so the whole fallback chain has time to recover. Capped so a run never
                # stalls for more than a few seconds per attempt.
                log.warning("agent_rate_limited", role=self.role, attempt=attempt, error=str(exc))
                if attempt > max_retries:
                    break
                await asyncio.sleep(min(2 ** attempt, 8))
            except (APIError, AgentError) as exc:
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
