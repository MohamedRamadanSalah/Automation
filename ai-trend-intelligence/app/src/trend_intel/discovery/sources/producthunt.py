"""Product Hunt GraphQL adapter (T044)."""
from __future__ import annotations

from typing import Any

import httpx

from trend_intel.core.errors import SourceError
from trend_intel.core.logging import get_logger
from trend_intel.core.utils import utcnow
from trend_intel.discovery.base import CandidateDTO

log = get_logger(__name__)

PH_API = "https://api.producthunt.com/v2/api/graphql"
_QUERY = """
query TrendingPosts($first: Int!) {
  posts(first: $first, order: VOTES) {
    edges {
      node {
        id name tagline votesCount website url
        topics { edges { node { slug } } }
      }
    }
  }
}
"""


class ProductHuntAdapter:
    key = "producthunt"

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        token = config.get("token", "")
        limit: int = config.get("limit", 20)
        timeout: float = config.get("timeout", 20.0)

        if not token:
            log.info("producthunt_skipped_no_token")
            return []

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    PH_API,
                    json={"query": _QUERY, "variables": {"first": limit}},
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
                resp.raise_for_status()
                edges = resp.json().get("data", {}).get("posts", {}).get("edges", [])
                candidates = [
                    CandidateDTO(
                        raw_name=edge["node"]["name"],
                        source_key=self.key,
                        url=edge["node"].get("website") or edge["node"].get("url"),
                        canonical_domain=None,
                        raw_signals={"votes": edge["node"].get("votesCount", 0)},
                        discovered_at=utcnow(),
                    )
                    for edge in edges
                ]
                log.info("producthunt_fetched", count=len(candidates))
                return candidates
        except Exception as exc:
            raise SourceError(f"ProductHunt fetch failed: {exc}") from exc
