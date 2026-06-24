"""SourceAdapter protocol and CandidateDTO."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class CandidateDTO:
    """Raw discovered item before validation."""
    raw_name: str
    source_key: str
    url: str | None = None
    canonical_domain: str | None = None
    raw_signals: dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=datetime.utcnow)


@runtime_checkable
class SourceAdapter(Protocol):
    """Every discovery source adapter must implement this interface."""

    @property
    def key(self) -> str:
        """Stable source identifier, e.g. 'hackernews'."""
        ...

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        """Fetch trending candidates from this source.

        Must return an empty list (not raise) on partial failure.
        May raise SourceError on total failure (caller will catch + skip).
        """
        ...
