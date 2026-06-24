"""Discovery stage coordinator (T028)."""
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


async def run_discover(run_id: uuid.UUID, session: AsyncSession) -> StageResult:
    run = await run_service.get_run(session, run_id)
    await run_service.transition_run(session, run, RunStatus.DISCOVERING)
    step = await run_service.start_step(session, run_id, "discovery")
    await session.commit()

    sources_result = await session.execute(select(DiscoverySource).where(DiscoverySource.enabled == True))
    sources = list(sources_result.scalars())

    if not sources:
        # No sources enabled — seed default hackernews
        default = DiscoverySource(key="hackernews", type="api", display_name="Hacker News", enabled=True, config={})
        session.add(default)
        await session.flush()
        sources = [default]

    skipped: list[str] = []
    total_candidates = 0

    async def _fetch_source(source: DiscoverySource) -> list[Candidate]:
        adapter = registry.get_adapter(source.key)
        if adapter is None:
            log.warning("no_adapter_for_source", key=source.key)
            return []
        try:
            dtos = await adapter.fetch(source.config or {})
            candidates = [
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
            return candidates
        except SourceError as exc:
            log.warning("source_failed", key=source.key, error=str(exc))
            skipped.append(source.key)
            return []

    results = await asyncio.gather(*[_fetch_source(s) for s in sources], return_exceptions=False)
    all_candidates: list[Candidate] = [c for batch in results for c in batch]

    for c in all_candidates:
        session.add(c)
        total_candidates += 1

    run.skipped_sources = skipped
    await run_service.finish_step(session, step, detail={"candidates": total_candidates, "skipped_sources": skipped})
    await session.commit()

    return StageResult(run_id=run_id, stage="discover", status="succeeded", detail={"candidates": total_candidates})


def _normalize(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]", "", name.lower())
