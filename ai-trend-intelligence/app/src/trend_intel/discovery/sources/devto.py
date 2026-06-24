"""Dev.to Forem API adapter (T043)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from trend_intel.core.errors import SourceError
from trend_intel.core.logging import get_logger
from trend_intel.discovery.base import CandidateDTO

log = get_logger(__name__)

DEVTO_ARTICLES = "https://dev.to/api/articles"
_TECH_TAGS = ["ai", "machinelearning", "python", "webdev", "opensource"]


class DevToAdapter:
    key = "devto"

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        limit: int = config.get("limit", 20)
        timeout: float = config.get("timeout", 15.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                candidates: list[CandidateDTO] = []
                for tag in _TECH_TAGS[:3]:
                    try:
                        resp = await client.get(DEVTO_ARTICLES, params={"tag": tag, "top": 7, "per_page": limit // len(_TECH_TAGS) + 1})
                        resp.raise_for_status()
                        for article in resp.json():
                            title = article.get("title", "")
                            url = article.get("url", "")
                            candidates.append(CandidateDTO(
                                raw_name=title[:100],
                                source_key=self.key,
                                url=url,
                                canonical_domain="dev.to",
                                raw_signals={"reactions": article.get("public_reactions_count", 0), "comments": article.get("comments_count", 0), "tag": tag},
                                discovered_at=datetime.now(timezone.utc),
                            ))
                    except Exception as exc:
                        log.warning("devto_tag_error", tag=tag, error=str(exc))
                log.info("devto_fetched", count=len(candidates))
                return candidates
        except Exception as exc:
            raise SourceError(f"Dev.to fetch failed: {exc}") from exc
