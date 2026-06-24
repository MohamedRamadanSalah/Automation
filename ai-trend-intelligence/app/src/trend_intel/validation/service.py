"""Validation service — normalize, dedup, popularity threshold (T029 MVP; upgraded in T047)."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.core.logging import get_logger
from trend_intel.models.candidates import Candidate
from trend_intel.models.tools import Tool

log = get_logger(__name__)


def _fuzzy_match(norm: str, seen: dict[str, "Tool"], threshold: int = 90) -> str | None:
    """Return the matching key from seen if rapidfuzz token_sort_ratio >= threshold."""
    try:
        from rapidfuzz.fuzz import token_sort_ratio
        for key in seen:
            if token_sort_ratio(norm, key) >= threshold:
                return key
    except Exception:
        pass
    return None


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation — canonical dedup key."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def make_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9\-]", "", name.lower().replace(" ", "-"))


async def validate_candidates(
    session: AsyncSession,
    run_id: uuid.UUID,
    config_snapshot: dict[str, Any],
) -> tuple[list[Tool], list[Candidate]]:
    """Validate candidates for run_id. Return (validated_tools, excluded_candidates)."""
    popularity_threshold = config_snapshot.get("popularity_threshold", 10)

    result = await session.execute(select(Candidate).where(Candidate.run_id == run_id, Candidate.validation_status == "pending"))
    candidates = list(result.scalars())

    seen_normalized: dict[str, Tool] = {}
    tools: list[Tool] = []
    excluded: list[Candidate] = []
    now = datetime.now(timezone.utc)

    for c in candidates:
        # Popularity threshold
        score = c.raw_signals.get("score", c.raw_signals.get("stars", c.raw_signals.get("upvotes", 0)))
        if isinstance(score, (int, float)) and score < popularity_threshold:
            c.validation_status = "excluded"
            c.exclusion_reason = f"popularity {score} < threshold {popularity_threshold}"
            excluded.append(c)
            continue

        norm = normalize_name(c.raw_name)
        if not norm:
            c.validation_status = "excluded"
            c.exclusion_reason = "empty normalized name"
            excluded.append(c)
            continue

        # Normalized + rapidfuzz fuzzy dedup (FR-004, token_sort_ratio ≥ 90)
        matched_key = _fuzzy_match(norm, seen_normalized, threshold=90)
        if matched_key is not None:
            norm = matched_key
        if norm in seen_normalized:
            existing_tool = seen_normalized[norm]
            existing_tool.source_refs = [*(existing_tool.source_refs or []), {"source": c.source_id and str(c.source_id), "url": c.url}]
            existing_tool.last_seen_at = now
            c.tool_id = existing_tool.id
            c.validation_status = "merged"
            continue

        # New tool
        existing_result = await session.execute(select(Tool).where(Tool.slug == make_slug(c.raw_name)))
        existing_tool = existing_result.scalar_one_or_none()
        if existing_tool:
            existing_tool.last_seen_at = now
            tool = existing_tool
        else:
            tool = Tool(
                canonical_name=c.raw_name,
                slug=make_slug(c.raw_name),
                homepage_url=c.url,
                first_seen_at=now,
                last_seen_at=now,
                source_refs=[{"source": str(c.source_id) if c.source_id else None, "url": c.url}],
            )
            session.add(tool)
            await session.flush()

        seen_normalized[norm] = tool
        c.tool_id = tool.id
        c.validation_status = "merged"
        tools.append(tool)

    log.info("validation_complete", run_id=str(run_id), validated=len(tools), excluded=len(excluded))
    return tools, excluded
