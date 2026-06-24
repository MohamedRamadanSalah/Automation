"""Hacker News adapter — Firebase API (no auth required)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from trend_intel.core.errors import SourceError
from trend_intel.core.logging import get_logger
from trend_intel.discovery.base import CandidateDTO

log = get_logger(__name__)

HN_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

_TECH_KEYWORDS = {"show hn", "ask hn", "launch", "open source", "github", "ai", "ml", "tool", "framework", "library"}


class HackerNewsAdapter:
    key = "hackernews"

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        limit: int = config.get("limit", 100)
        min_score: int = config.get("min_score", 50)
        timeout: float = config.get("timeout", 20.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(HN_TOP_STORIES)
                resp.raise_for_status()
                story_ids: list[int] = resp.json()[:limit]

                candidates: list[CandidateDTO] = []
                for story_id in story_ids[:50]:  # cap HTTP calls
                    try:
                        item_resp = await client.get(HN_ITEM.format(id=story_id))
                        item_resp.raise_for_status()
                        item = item_resp.json()
                        if not item or item.get("type") != "story":
                            continue
                        score = item.get("score", 0)
                        if score < min_score:
                            continue
                        title = item.get("title", "")
                        url = item.get("url", "")
                        domain = urlparse(url).netloc if url else None
                        candidates.append(
                            CandidateDTO(
                                raw_name=title,
                                source_key=self.key,
                                url=url or None,
                                canonical_domain=domain,
                                raw_signals={"score": score, "comments": item.get("descendants", 0), "hn_id": story_id},
                                discovered_at=datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc),
                            )
                        )
                    except Exception as exc:
                        log.warning("hn_item_fetch_error", story_id=story_id, error=str(exc))

                log.info("hn_fetched", count=len(candidates))
                return candidates

        except Exception as exc:
            raise SourceError(f"HackerNews fetch failed: {exc}") from exc
