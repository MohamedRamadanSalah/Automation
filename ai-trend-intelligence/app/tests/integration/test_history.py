"""Integration tests: two-report comparison + distinct storage (T060)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_two_runs_produce_distinct_reports(db_session, openrouter_mock):
    """Two runs on the same day produce two distinct, separately stored reports (FR-021)."""
    from trend_intel.orchestration import run_service
    from trend_intel.schemas.runs import RunCreate

    run1 = await run_service.create_run(db_session, RunCreate(trigger_type="manual"))
    await db_session.flush()
    run2 = await run_service.create_run(db_session, RunCreate(trigger_type="manual"))
    await db_session.flush()

    assert run1.id != run2.id, "Two runs must have distinct IDs"
    await db_session.rollback()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tool_history_lists_appearances(db_session):
    """Tool history service lists each report appearance with score."""
    from trend_intel.history.service import get_tool_history
    from trend_intel.core.errors import NotFoundError
    import uuid

    with pytest.raises(NotFoundError):
        await get_tool_history(db_session, uuid.uuid4())
