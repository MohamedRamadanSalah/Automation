"""Reddit OAuth API adapter (T042)."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from trend_intel.core.errors import SourceError
from trend_intel.core.logging import get_logger
from trend_intel.core.utils import utcnow
from trend_intel.discovery.base import CandidateDTO

log = get_logger(__name__)

REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_SEARCH_URL = "https://oauth.reddit.com/r/{sub}/hot"

_SUBREDDITS = ["MachineLearning", "artificial", "LocalLLaMA", "Python", "programming"]


class RedditAdapter:
    key = "reddit"

    async def _get_token(self, client_id: str, client_secret: str, user_agent: str, client: httpx.AsyncClient) -> str:
        resp = await client.post(
            REDDIT_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"User-Agent": user_agent},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        client_id = config.get("client_id", "")
        client_secret = config.get("client_secret", "")
        user_agent = config.get("user_agent", "TrendIntel/1.0")
        limit: int = config.get("limit", 25)
        min_score: int = config.get("min_score", 50)

        if not client_id or not client_secret:
            log.info("reddit_skipped_no_credentials")
            return []

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                token = await self._get_token(client_id, client_secret, user_agent, client)
                headers = {"Authorization": f"Bearer {token}", "User-Agent": user_agent}
                candidates: list[CandidateDTO] = []
                for sub in _SUBREDDITS[:3]:
                    try:
                        resp = await client.get(REDDIT_SEARCH_URL.format(sub=sub), params={"limit": limit}, headers=headers)
                        resp.raise_for_status()
                        posts = resp.json().get("data", {}).get("children", [])
                        for post in posts:
                            d = post.get("data", {})
                            if d.get("score", 0) < min_score:
                                continue
                            title = d.get("title", "")
                            url = d.get("url", "")
                            candidates.append(CandidateDTO(
                                raw_name=title[:100],
                                source_key=self.key,
                                url=url or None,
                                canonical_domain=urlparse(url).netloc if url else None,
                                raw_signals={"score": d.get("score", 0), "comments": d.get("num_comments", 0), "subreddit": sub},
                                discovered_at=utcnow(),
                            ))
                    except Exception as exc:
                        log.warning("reddit_sub_error", sub=sub, error=str(exc))
                log.info("reddit_fetched", count=len(candidates))
                return candidates
        except Exception as exc:
            raise SourceError(f"Reddit fetch failed: {exc}") from exc
