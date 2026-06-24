"""RSS/Atom adapter — Medium, tech blogs, AI news (T045)."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import feedparser

from trend_intel.core.errors import SourceError
from trend_intel.core.logging import get_logger
from trend_intel.core.utils import utcnow
from trend_intel.discovery.base import CandidateDTO

log = get_logger(__name__)

DEFAULT_FEEDS = [
    "https://medium.com/feed/tag/artificial-intelligence",
    "https://medium.com/feed/tag/python",
    "https://feeds.feedburner.com/TechCrunch/",
    "https://www.infoq.com/feed/",
]


class RSSAdapter:
    key = "rss"

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        feeds: list[str] = config.get("feeds", DEFAULT_FEEDS)
        limit_per_feed: int = config.get("limit_per_feed", 10)

        try:
            candidates: list[CandidateDTO] = []
            for feed_url in feeds:
                try:
                    parsed = feedparser.parse(feed_url)
                    if parsed.bozo and not parsed.entries:
                        log.warning("rss_feed_error", url=feed_url)
                        continue
                    for entry in parsed.entries[:limit_per_feed]:
                        title = entry.get("title", "")
                        url = entry.get("link", "")
                        domain = urlparse(feed_url).netloc
                        candidates.append(CandidateDTO(
                            raw_name=title[:150],
                            source_key=self.key,
                            url=url,
                            canonical_domain=domain,
                            raw_signals={"feed": feed_url, "source_domain": domain},
                            discovered_at=utcnow(),
                        ))
                except Exception as exc:
                    log.warning("rss_entry_error", feed=feed_url, error=str(exc))

            log.info("rss_fetched", count=len(candidates))
            return candidates
        except Exception as exc:
            raise SourceError(f"RSS fetch failed: {exc}") from exc
