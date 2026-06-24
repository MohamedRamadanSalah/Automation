"""HTTP fetch + article extraction (T046)."""
from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
import trafilatura
from selectolax.parser import HTMLParser

from trend_intel.core.logging import get_logger

log = get_logger(__name__)

MAX_CONTENT_BYTES = 2 * 1024 * 1024  # 2 MB cap
ALLOWED_SCHEMES = {"http", "https"}
TIMEOUT = 15.0


def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ALLOWED_SCHEMES and bool(parsed.netloc)
    except Exception:
        return False


async def fetch_url(url: str) -> str:
    """Fetch URL and extract article text. Returns empty string on failure."""
    if not _is_safe_url(url):
        log.warning("unsafe_url_blocked", url=url[:100])
        return ""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, max_redirects=3) as client:
            resp = await client.get(url, headers={"User-Agent": "TrendIntel/1.0 (+https://github.com/)"})
            resp.raise_for_status()
            if len(resp.content) > MAX_CONTENT_BYTES:
                log.warning("fetch_size_cap", url=url[:100], size=len(resp.content))
                return ""
            content_type = resp.headers.get("content-type", "")
            if "html" not in content_type and "text" not in content_type:
                return ""
            html = resp.text
    except Exception as exc:
        log.warning("fetch_failed", url=url[:100], error=str(exc))
        return ""

    # Try trafilatura first (best for articles)
    extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
    if extracted and len(extracted) > 100:
        return extracted[:4000]

    # Fallback: selectolax to strip tags
    try:
        tree = HTMLParser(html)
        for tag in tree.css("script, style, nav, footer, header"):
            tag.decompose()
        text = tree.body.text(separator=" ") if tree.body else ""
        text = re.sub(r"\s+", " ", text).strip()
        return text[:4000]
    except Exception:
        return ""
