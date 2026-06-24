"""Structured logging with secret-redaction processor (FR-027, SC-011)."""
from __future__ import annotations

import re
import structlog
from structlog.types import EventDict, WrappedLogger

_SECRET_ENV_VARS = frozenset(
    {
        "openrouter_api_key",
        "api_key",
        "postgres_password",
        "n8n_basic_auth_password",
        "n8n_encryption_key",
        "github_token",
        "reddit_client_secret",
        "producthunt_token",
    }
)

_REDACTED = "[REDACTED]"
_VALUE_RE = re.compile(r"(sk-or-[A-Za-z0-9\-]{8,}|Bearer\s+\S+)", re.IGNORECASE)


def redact_secrets(logger: WrappedLogger, method: str, event_dict: EventDict) -> EventDict:
    """Walk the event dict and mask known secret keys and value patterns."""
    _redact_dict(event_dict)
    return event_dict


def _redact_dict(d: dict) -> None:  # type: ignore[type-arg]
    for key, value in list(d.items()):
        if isinstance(key, str) and key.lower() in _SECRET_ENV_VARS:
            d[key] = _REDACTED
        elif isinstance(value, dict):
            _redact_dict(value)
        elif isinstance(value, str):
            d[key] = _VALUE_RE.sub(_REDACTED, value)
        elif isinstance(value, (list, tuple)):
            d[key] = [
                _VALUE_RE.sub(_REDACTED, v) if isinstance(v, str) else v for v in value
            ]


def configure_logging(log_level: str = "INFO") -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            redact_secrets,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            __import__("logging").getLevelName(log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return structlog.get_logger(name)
