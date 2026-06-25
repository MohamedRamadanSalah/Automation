"""Hacker News Algolia API adapter — topic-based and date-range search."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from trend_intel.core.errors import SourceError
from trend_intel.core.logging import get_logger
from trend_intel.core.utils import utcnow
from trend_intel.discovery.base import CandidateDTO

log = get_logger(__name__)

HN_ALGOLIA = "https://hn.algolia.com/api/v1/search"

DEFAULT_QUERIES: list[str] = [
    # AI Engineering
    "LLM production engineering tool",
    "RAG retrieval augmented generation framework",
    "AI agents open source",
    "fine-tuning language model technique",
    "MLOps machine learning platform",
    "vector database embedding",
    "prompt engineering",
    "AI infrastructure deployment",
    # AI Skills & Career
    "AI engineer skills requirements",
    "machine learning engineer career",
    # Flutter
    "Flutter framework Dart release",
    "Flutter mobile development package",
    "Flutter performance best practices",
    # .NET Backend
    ".NET C# backend framework",
    "ASP.NET Core microservices performance",
    "Entity Framework Core",
    "C# new features",
    # Systems Design & Architecture
    "system design distributed architecture",
    "software architecture patterns microservices",
    "distributed systems scalability",
    # Software Engineering
    "software engineering best practices",
    "clean code architecture refactoring",
    # Job Market & Skills
    "software engineer job requirements AI skills",
    "tech hiring trends demand 2025",
    "what companies look for software engineers",
]


class HNAlgoliaAdapter:
    key = "hn_algolia"

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        queries: list[str] = config.get("queries", DEFAULT_QUERIES)
        days_back: int = config.get("days_back", 30)
        min_points: int = config.get("min_points", 10)
        per_query: int = config.get("per_query", 15)
        timeout: float = config.get("timeout", 30.0)
        batch_size: int = config.get("batch_size", 5)

        since_ts = int(
            (datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp()
        )
        seen: set[str] = set()
        candidates: list[CandidateDTO] = []

        async def _fetch_query(query: str) -> list[CandidateDTO]:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.get(
                        HN_ALGOLIA,
                        params={
                            "query": query,
                            "tags": "story",
                            "numericFilters": json.dumps([f"points>{min_points}", f"created_at_i>{since_ts}"]),
                            "hitsPerPage": per_query,
                        },
                    )
                    resp.raise_for_status()
                    results = []
                    for hit in resp.json().get("hits", []):
                        hit_id = str(hit.get("objectID") or "")
                        if not hit_id or hit_id in seen:
                            continue
                        seen.add(hit_id)
                        title = (hit.get("title") or "").strip()
                        if not title:
                            continue
                        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit_id}"
                        domain = urlparse(url).netloc if url else "news.ycombinator.com"
                        points = hit.get("points") or 0
                        created_ts = hit.get("created_at_i")
                        discovered = (
                            datetime.fromtimestamp(created_ts, tz=timezone.utc).replace(tzinfo=None)
                            if created_ts
                            else utcnow()
                        )
                        results.append(
                            CandidateDTO(
                                raw_name=title[:150],
                                source_key=self.key,
                                url=url,
                                canonical_domain=domain,
                                raw_signals={
                                    "score": points,
                                    "points": points,
                                    "comments": hit.get("num_comments") or 0,
                                    "hn_id": hit_id,
                                    "query": query,
                                },
                                discovered_at=discovered,
                            )
                        )
                    return results
            except Exception as exc:
                log.warning("hn_algolia_query_error", query=query, error=str(exc))
                return []

        try:
            for i in range(0, len(queries), batch_size):
                batch = queries[i : i + batch_size]
                batch_results = await asyncio.gather(*[_fetch_query(q) for q in batch])
                for results in batch_results:
                    candidates.extend(results)
                if i + batch_size < len(queries):
                    await asyncio.sleep(0.5)

            log.info("hn_algolia_fetched", count=len(candidates))
            return candidates
        except Exception as exc:
            raise SourceError(f"HN Algolia fetch failed: {exc}") from exc
