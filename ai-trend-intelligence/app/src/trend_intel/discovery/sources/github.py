"""GitHub Search API trending adapter (T041)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from trend_intel.core.errors import SourceError
from trend_intel.core.logging import get_logger
from trend_intel.discovery.base import CandidateDTO

log = get_logger(__name__)

GH_SEARCH = "https://api.github.com/search/repositories"


class GitHubAdapter:
    key = "github"

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        token = config.get("token", "")
        limit: int = config.get("limit", 30)
        days_back: int = config.get("days_back", 7)
        timeout: float = config.get("timeout", 20.0)

        since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        params = {"q": f"created:>{since} stars:>50 language:python", "sort": "stars", "order": "desc", "per_page": limit}
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(GH_SEARCH, params=params, headers=headers)
                resp.raise_for_status()
                items = resp.json().get("items", [])
                candidates = [
                    CandidateDTO(
                        raw_name=item["name"],
                        source_key=self.key,
                        url=item.get("html_url"),
                        canonical_domain="github.com",
                        raw_signals={"stars": item.get("stargazers_count", 0), "forks": item.get("forks_count", 0), "language": item.get("language", "")},
                        discovered_at=datetime.now(timezone.utc),
                    )
                    for item in items
                ]
                log.info("github_fetched", count=len(candidates))
                return candidates
        except Exception as exc:
            raise SourceError(f"GitHub fetch failed: {exc}") from exc
