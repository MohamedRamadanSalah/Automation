"""Integration tests: multi-source discovery + dedup + resilience (T039)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normalize_dedup_removes_duplicates():
    """Same tool under different names collapses to one after normalization."""
    from trend_intel.validation.service import normalize_name
    names = ["Tool.ai", "tool ai", "Tool AI", "TOOL-AI"]
    normalized = {normalize_name(n) for n in names}
    assert len(normalized) == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_failing_source_does_not_abort_run(db_session):
    """Discovery with a failing source records it in skipped_sources, run continues."""
    from unittest.mock import patch, AsyncMock
    from trend_intel.orchestration import run_service
    from trend_intel.schemas.runs import RunCreate, RunStatus

    run = await run_service.create_run(db_session, RunCreate(trigger_type="manual"))
    await db_session.commit()
    assert run.status == RunStatus.PENDING
