"""Unit tests: normalized+fuzzy dedup (T038)."""
from __future__ import annotations

import pytest
from trend_intel.validation.service import normalize_name, make_slug


def test_normalize_removes_punctuation():
    assert normalize_name("Tool.AI") == "toolai"
    assert normalize_name("Tool AI") == "toolai"
    assert normalize_name("tool-ai") == "toolai"
    assert normalize_name("TOOL AI") == "toolai"


def test_normalize_same_tool_variants():
    variants = ["Tool.ai", "Tool AI", "tool-ai", "ToolAI", "  tool ai  "]
    normalized = {normalize_name(v) for v in variants}
    assert len(normalized) == 1, f"Expected 1 normalized form, got: {normalized}"


def test_make_slug():
    assert make_slug("Tool AI") == "tool-ai"
    assert make_slug("LangChain") == "langchain"
    assert make_slug("Next.js") == "nextjs"


def test_normalize_empty():
    assert normalize_name("") == ""
    assert normalize_name("   ") == ""
    assert normalize_name("!!!") == ""
