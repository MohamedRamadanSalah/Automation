"""Config-driven adapter registry (FR-023)."""
from __future__ import annotations

from typing import Any

from trend_intel.core.logging import get_logger
from trend_intel.discovery.base import SourceAdapter
from trend_intel.discovery.sources.hackernews import HackerNewsAdapter

log = get_logger(__name__)

_BUILTIN_ADAPTERS: dict[str, SourceAdapter] = {
    "hackernews": HackerNewsAdapter(),
}

# Additional adapters registered at import time (US2 adds github/reddit/etc.)
_registry: dict[str, SourceAdapter] = dict(_BUILTIN_ADAPTERS)


def register(adapter: SourceAdapter) -> None:
    _registry[adapter.key] = adapter


def get_adapter(key: str) -> SourceAdapter | None:
    return _registry.get(key)


def all_adapters() -> dict[str, SourceAdapter]:
    return dict(_registry)
