"""Tenacity-based bounded retry helper (FR-025)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from trend_intel.core.logging import get_logger

log = get_logger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


def bounded_retry(
    *,
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    reraise_types: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator: retry up to max_attempts with exponential backoff."""

    def _log_retry(retry_state: Any) -> None:
        log.warning(
            "retry",
            attempt=retry_state.attempt_number,
            fn=getattr(retry_state.fn, "__name__", "?"),
            error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
        )

    return retry(  # type: ignore[return-value]
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(reraise_types),
        before_sleep=_log_retry,
        reraise=True,
    )


__all__ = ["bounded_retry", "RetryError"]
