"""GitHub Search API — multi-topic trending adapter."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from trend_intel.core.errors import SourceError
from trend_intel.core.logging import get_logger
from trend_intel.core.utils import utcnow
from trend_intel.discovery.base import CandidateDTO

log = get_logger(__name__)

GH_SEARCH = "https://api.github.com/search/repositories"

# (query_string, category, min_stars)
TOPIC_SEARCHES: list[tuple[str, str, int]] = [
    # AI Engineering & LLM
    ("topic:llm language:python",               "ai_engineering",       30),
    ("topic:rag language:python",               "ai_engineering",       20),
    ("topic:ai-agents",                          "ai_engineering",       20),
    ("topic:vector-database",                   "ai_engineering",       50),
    ("topic:langchain",                         "ai_engineering",       20),
    ("topic:mlops language:python",             "ai_engineering",       30),
    ("topic:fine-tuning",                       "ai_engineering",       10),
    # Flutter & Dart
    ("language:dart topic:flutter",             "flutter",              30),
    ("topic:flutter-packages",                  "flutter",              15),
    # .NET Backend
    ("language:csharp topic:dotnet",            "dotnet",               30),
    ("topic:aspnetcore",                        "dotnet",               20),
    ("topic:entityframework",                   "dotnet",               15),
    # Systems Design & Architecture
    ("topic:system-design",                     "systems_design",      100),
    ("topic:distributed-systems",              "systems_design",       50),
    # Software Engineering
    ("topic:clean-architecture",               "software_engineering", 50),
    ("topic:design-patterns stars:>100",       "software_engineering", 100),
]


class GitHubAdapter:
    key = "github"

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        token: str = config.get("token", "")
        days_back: int = config.get("days_back", 14)
        per_topic: int = config.get("per_topic", 10)
        timeout: float = config.get("timeout", 30.0)
        topic_searches: list[tuple] = config.get("topic_searches", TOPIC_SEARCHES)

        since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        seen: set[str] = set()
        candidates: list[CandidateDTO] = []
        # Rate limits: 30 req/min with token, 10 req/min without
        delay = 2.5 if token else 7.0

        async def _search_one(q_str: str, category: str, min_stars: int) -> list[CandidateDTO]:
            params = {
                "q": f"{q_str} pushed:>{since} stars:>{min_stars}",
                "sort": "stars",
                "order": "desc",
                "per_page": per_topic,
            }
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.get(GH_SEARCH, params=params, headers=headers)
                    if resp.status_code == 422:
                        return []
                    resp.raise_for_status()
                    results = []
                    for item in resp.json().get("items", []):
                        full_name = item.get("full_name", "")
                        if full_name in seen:
                            continue
                        seen.add(full_name)
                        stars = item.get("stargazers_count", 0)
                        results.append(CandidateDTO(
                            raw_name=item.get("name", full_name),
                            source_key=self.key,
                            url=item.get("html_url"),
                            canonical_domain="github.com",
                            raw_signals={
                                "score": stars,
                                "stars": stars,
                                "forks": item.get("forks_count", 0),
                                "language": item.get("language", ""),
                                "description": (item.get("description") or "")[:200],
                                "full_name": full_name,
                                "category": category,
                            },
                            discovered_at=utcnow(),
                        ))
                    return results
            except Exception as exc:
                log.warning("github_search_error", query=q_str, error=str(exc))
                return []

        try:
            for q_str, category, min_stars in topic_searches:
                batch = await _search_one(q_str, category, min_stars)
                candidates.extend(batch)
                await asyncio.sleep(delay)

            log.info("github_fetched", count=len(candidates))
            return candidates
        except Exception as exc:
            raise SourceError(f"GitHub fetch failed: {exc}") from exc
