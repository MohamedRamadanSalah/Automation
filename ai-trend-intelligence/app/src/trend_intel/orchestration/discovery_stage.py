"""Discovery stage coordinator."""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.core.errors import SourceError
from trend_intel.core.utils import utcnow
from trend_intel.core.logging import get_logger
from trend_intel.discovery import registry
from trend_intel.models.candidates import Candidate
from trend_intel.models.discovery_sources import DiscoverySource
from trend_intel.orchestration import run_service
from trend_intel.schemas.runs import RunStatus, StageResult

log = get_logger(__name__)

# Seeded on first run when discovery_sources table is empty
_DEFAULT_SOURCES = [
    {
        "key": "hackernews",
        "type": "api",
        "display_name": "Hacker News Top Stories",
        "config": {"min_score": 30, "limit": 100},
    },
    {
        "key": "hn_algolia",
        "type": "api",
        "display_name": "HN Algolia Topic Search",
        "config": {},
    },
    {
        "key": "github",
        "type": "api",
        "display_name": "GitHub Trending Multi-Topic",
        "config": {},
    },
    {
        "key": "devto",
        "type": "api",
        "display_name": "Dev.to Articles",
        "config": {},
    },
    {
        "key": "rss",
        "type": "rss",
        "display_name": "Tech RSS Feeds",
        "config": {},
    },
]

# Injected into all source configs for backfill runs (~4 months of history)
_BACKFILL_OVERRIDES: dict = {
    "days_back": 120,
    "per_query": 20,
    "per_topic": 15,
    "limit_per_feed": 20,
    "limit": 100,
    "min_points": 5,
}


async def run_discover(run_id: uuid.UUID, session: AsyncSession) -> StageResult:
    run = await run_service.get_run(session, run_id)
    await run_service.transition_run(session, run, RunStatus.DISCOVERING)
    step = await run_service.start_step(session, run_id, "discovery")
    await session.commit()

    backfill: bool = bool(run.config_snapshot.get("backfill", False))

    sources_result = await session.execute(
        select(DiscoverySource).where(DiscoverySource.enabled == True)
    )
    sources = list(sources_result.scalars())

    if not sources:
        for ds_def in _DEFAULT_SOURCES:
            session.add(
                DiscoverySource(
                    key=ds_def["key"],
                    type=ds_def["type"],
                    display_name=ds_def["display_name"],
                    enabled=True,
                    config=ds_def["config"],
                )
            )
        await session.flush()
        res2 = await session.execute(
            select(DiscoverySource).where(DiscoverySource.enabled == True)
        )
        sources = list(res2.scalars())

    skipped: list[str] = []
    total_candidates = 0

    async def _fetch_source(source: DiscoverySource) -> list[Candidate]:
        # Allow config to specify a different adapter via "adapter" key
        effective_config = dict(source.config or {})
        adapter_key = effective_config.pop("adapter", source.key)
        adp = registry.get_adapter(adapter_key)
        if adp is None:
            log.warning("no_adapter_for_source", key=source.key, adapter=adapter_key)
            return []

        if backfill:
            effective_config.update(_BACKFILL_OVERRIDES)

        try:
            dtos = await adp.fetch(effective_config)
            return [
                Candidate(
                    run_id=run_id,
                    source_id=source.id,
                    raw_name=dto.raw_name,
                    normalized_name=_normalize(dto.raw_name),
                    url=dto.url,
                    canonical_domain=dto.canonical_domain,
                    raw_signals=dto.raw_signals,
                    discovered_at=dto.discovered_at or utcnow(),
                    validation_status="pending",
                )
                for dto in dtos
            ]
        except SourceError as exc:
            log.warning("source_failed", key=source.key, error=str(exc))
            skipped.append(source.key)
            return []

    results = await asyncio.gather(
        *[_fetch_source(s) for s in sources], return_exceptions=False
    )
    all_candidates: list[Candidate] = [c for batch in results for c in batch]

    for c in all_candidates:
        session.add(c)
        total_candidates += 1

    run.skipped_sources = skipped
    await run_service.finish_step(
        session,
        step,
        detail={
            "candidates": total_candidates,
            "skipped_sources": skipped,
            "backfill": backfill,
        },
    )
    await session.commit()

    return StageResult(
        run_id=run_id,
        stage="discover",
        status="succeeded",
        detail={"candidates": total_candidates},
    )


def _normalize(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]", "", name.lower())
