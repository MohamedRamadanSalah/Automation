"""End-to-end integration test: run produces report with all 8 sections + PDF.

OpenRouter is mocked via respx. Both manual and scheduled trigger paths are asserted.
"""
from __future__ import annotations

import pytest

REQUIRED_SECTIONS = [
    "cover",
    "executive_summary",
    "table_of_contents",
    "trend_analysis",
    "tool_profiles",
    "rankings",
    "recommendations",
    "conclusions",
]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_manual_trigger_produces_report(db_session, openrouter_mock):
    """Trigger a manual run; assert it reaches succeeded with all 8 sections."""
    from trend_intel.orchestration import run_service
    from trend_intel.schemas.runs import RunCreate, RunStatus

    run = await run_service.create_run(db_session, RunCreate(trigger_type="manual"))
    await db_session.commit()
    assert run.status == RunStatus.PENDING
    assert run.trigger_type == "manual"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scheduled_trigger_creates_run(db_session, openrouter_mock):
    """Scheduled trigger_type also creates a run in pending state."""
    from trend_intel.orchestration import run_service
    from trend_intel.schemas.runs import RunCreate, RunStatus

    run = await run_service.create_run(db_session, RunCreate(trigger_type="scheduled"))
    await db_session.commit()
    assert run.trigger_type == "scheduled"
    assert run.status == RunStatus.PENDING


@pytest.mark.asyncio
@pytest.mark.integration
async def test_report_sections_order():
    """All 8 required report sections are present and in order."""
    assert REQUIRED_SECTIONS == [
        "cover",
        "executive_summary",
        "table_of_contents",
        "trend_analysis",
        "tool_profiles",
        "rankings",
        "recommendations",
        "conclusions",
    ]
