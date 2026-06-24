"""Unit tests for source adapters — parsing fixtures (T078)."""
from __future__ import annotations

import pytest


def test_normalize_hn_title():
    """HN candidate title is cleaned correctly."""
    from trend_intel.validation.service import normalize_name
    assert normalize_name("Show HN: My Cool Tool") == "showhnmycooltool"


def test_rss_adapter_default_feeds():
    from trend_intel.discovery.sources.rss import DEFAULT_FEEDS
    assert len(DEFAULT_FEEDS) > 0
    for feed in DEFAULT_FEEDS:
        assert feed.startswith("http")


def test_github_adapter_key():
    from trend_intel.discovery.sources.github import GitHubAdapter
    adapter = GitHubAdapter()
    assert adapter.key == "github"


def test_reddit_adapter_key():
    from trend_intel.discovery.sources.reddit import RedditAdapter
    adapter = RedditAdapter()
    assert adapter.key == "reddit"


def test_devto_adapter_key():
    from trend_intel.discovery.sources.devto import DevToAdapter
    adapter = DevToAdapter()
    assert adapter.key == "devto"


def test_producthunt_adapter_key():
    from trend_intel.discovery.sources.producthunt import ProductHuntAdapter
    adapter = ProductHuntAdapter()
    assert adapter.key == "producthunt"


def test_all_adapters_registered():
    from trend_intel.discovery.registry import all_adapters
    adapters = all_adapters()
    expected = {"hackernews", "github", "reddit", "devto", "producthunt", "rss"}
    assert expected.issubset(set(adapters.keys()))


@pytest.mark.asyncio
async def test_reddit_returns_empty_without_credentials():
    """Reddit adapter returns empty list if credentials not set."""
    from trend_intel.discovery.sources.reddit import RedditAdapter
    adapter = RedditAdapter()
    result = await adapter.fetch({"client_id": "", "client_secret": ""})
    assert result == []


@pytest.mark.asyncio
async def test_producthunt_returns_empty_without_token():
    """ProductHunt adapter returns empty list if token not set."""
    from trend_intel.discovery.sources.producthunt import ProductHuntAdapter
    adapter = ProductHuntAdapter()
    result = await adapter.fetch({"token": ""})
    assert result == []
