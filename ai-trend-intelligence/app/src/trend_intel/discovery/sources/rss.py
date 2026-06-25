"""RSS/Atom adapter — multi-domain feed coverage with date filtering."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import feedparser

from trend_intel.core.errors import SourceError
from trend_intel.core.logging import get_logger
from trend_intel.core.utils import utcnow
from trend_intel.discovery.base import CandidateDTO

log = get_logger(__name__)

DEFAULT_FEEDS: list[str] = [
    # AI Engineering
    "https://huggingface.co/blog/feed.xml",
    "https://blog.langchain.dev/rss/",
    "https://medium.com/feed/tag/llm",
    "https://medium.com/feed/tag/artificial-intelligence",
    # Flutter
    "https://medium.com/feed/flutter",
    "https://dev.to/feed/tag/flutter",
    # .NET Backend
    "https://devblogs.microsoft.com/dotnet/feed/",
    "https://dev.to/feed/tag/dotnet",
    "https://dev.to/feed/tag/csharp",
    # Systems Design & Architecture
    "https://martinfowler.com/feed.atom",
    "https://www.infoq.com/feed/",
    "https://highscalability.com/rss/",
    # Software Engineering & Tech
    "https://netflixtechblog.com/feed",
    "https://medium.com/feed/tag/software-engineering",
    "https://feeds.feedburner.com/TechCrunch/",
]

# Feed domain → category classification
_CATEGORY_MAP: dict[str, str] = {
    "huggingface.co": "ai_engineering",
    "langchain.dev": "ai_engineering",
    "deeplearning.ai": "ai_engineering",
    "devblogs.microsoft.com": "dotnet",
    "martinfowler.com": "systems_design",
    "infoq.com": "systems_design",
    "highscalability.com": "systems_design",
    "netflixtechblog.com": "software_engineering",
    "dev.to": "general",
    "medium.com": "general",
}


class RSSAdapter:
    key = "rss"

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        feeds: list[str] = config.get("feeds", DEFAULT_FEEDS)
        limit_per_feed: int = config.get("limit_per_feed", 12)
        days_back: int = config.get("days_back", 30)

        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
        seen_urls: set[str] = set()
        candidates: list[CandidateDTO] = []

        try:
            for feed_url in feeds:
                try:
                    parsed = feedparser.parse(feed_url)
                    if parsed.bozo and not parsed.entries:
                        log.warning("rss_feed_error", url=feed_url)
                        continue

                    feed_domain = urlparse(feed_url).netloc.replace("www.", "")
                    category = _CATEGORY_MAP.get(feed_domain, "general")
                    count = 0

                    for entry in parsed.entries:
                        if count >= limit_per_feed:
                            break
                        title = (entry.get("title") or "").strip()[:150]
                        url = entry.get("link", "")
                        if not title or not url or url in seen_urls:
                            continue

                        # Date filter — skip entries older than days_back
                        published = entry.get("published_parsed") or entry.get("updated_parsed")
                        if published:
                            try:
                                pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                                if pub_dt < cutoff_dt:
                                    continue
                            except Exception:
                                pass

                        seen_urls.add(url)
                        count += 1
                        candidates.append(
                            CandidateDTO(
                                raw_name=title,
                                source_key=self.key,
                                url=url,
                                canonical_domain=feed_domain,
                                raw_signals={
                                    "score": 15,
                                    "feed": feed_url,
                                    "category": category,
                                },
                                discovered_at=utcnow(),
                            )
                        )
                except Exception as exc:
                    log.warning("rss_feed_parse_error", url=feed_url, error=str(exc))

            log.info("rss_fetched", count=len(candidates))
            return candidates
        except Exception as exc:
            raise SourceError(f"RSS fetch failed: {exc}") from exc
