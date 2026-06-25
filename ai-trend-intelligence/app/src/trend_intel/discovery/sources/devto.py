"""Dev.to Forem API adapter — multi-domain tag coverage."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from trend_intel.core.errors import SourceError
from trend_intel.core.logging import get_logger
from trend_intel.core.utils import utcnow
from trend_intel.discovery.base import CandidateDTO

log = get_logger(__name__)

DEVTO_ARTICLES = "https://dev.to/api/articles"

# (tag, category)
DOMAIN_TAGS: list[tuple[str, str]] = [
    # AI Engineering
    ("ai",                  "ai_engineering"),
    ("machinelearning",     "ai_engineering"),
    ("llm",                 "ai_engineering"),
    ("mlops",               "ai_engineering"),
    # Flutter
    ("flutter",             "flutter"),
    ("dart",                "flutter"),
    # .NET Backend
    ("dotnet",              "dotnet"),
    ("csharp",              "dotnet"),
    # Systems Design
    ("systemdesign",        "systems_design"),
    ("architecture",        "systems_design"),
    # Software Engineering
    ("programming",         "software_engineering"),
    ("devops",              "software_engineering"),
    # Career / Job Market
    ("career",              "job_market"),
    ("productivity",        "job_market"),
]


class DevToAdapter:
    key = "devto"

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        tags: list[tuple[str, str]] = config.get("tags", DOMAIN_TAGS)
        per_tag: int = config.get("per_tag", 8)
        timeout: float = config.get("timeout", 20.0)

        seen_ids: set[int] = set()
        candidates: list[CandidateDTO] = []

        async def _fetch_tag(tag: str, category: str) -> list[CandidateDTO]:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.get(
                        DEVTO_ARTICLES,
                        params={"tag": tag, "top": 7, "per_page": per_tag},
                    )
                    resp.raise_for_status()
                    results = []
                    for article in resp.json():
                        art_id = article.get("id")
                        if art_id in seen_ids:
                            continue
                        seen_ids.add(art_id)
                        reactions = article.get("public_reactions_count") or 0
                        title = (article.get("title") or "").strip()[:150]
                        url = article.get("url", "")
                        if not title:
                            continue
                        results.append(
                            CandidateDTO(
                                raw_name=title,
                                source_key=self.key,
                                url=url,
                                canonical_domain="dev.to",
                                raw_signals={
                                    "score": reactions,
                                    "reactions": reactions,
                                    "comments": article.get("comments_count") or 0,
                                    "tag": tag,
                                    "category": category,
                                },
                                discovered_at=utcnow(),
                            )
                        )
                    return results
            except Exception as exc:
                log.warning("devto_tag_error", tag=tag, error=str(exc))
                return []

        try:
            for i in range(0, len(tags), 4):
                batch = tags[i : i + 4]
                batch_results = await asyncio.gather(*[_fetch_tag(t, c) for t, c in batch])
                for results in batch_results:
                    candidates.extend(results)
                await asyncio.sleep(0.3)

            log.info("devto_fetched", count=len(candidates))
            return candidates
        except Exception as exc:
            raise SourceError(f"Dev.to fetch failed: {exc}") from exc
