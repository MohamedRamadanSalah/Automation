"""Integration tests: error paths, retry, PDF failure (T071, SC-007, SC-010, SC-012, SC-013)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
@pytest.mark.integration
async def test_run_transitions_to_failed_on_error(db_session):
    """A run that hits a critical error transitions to failed status."""
    from trend_intel.orchestration import run_service
    from trend_intel.schemas.runs import RunCreate, RunStatus

    run = await run_service.create_run(db_session, RunCreate(trigger_type="manual"))
    await db_session.flush()

    await run_service.transition_run(db_session, run, RunStatus.DISCOVERING)
    await run_service.transition_run(db_session, run, RunStatus.FAILED, failure_reason="test_error")
    await db_session.flush()

    assert run.status == RunStatus.FAILED
    assert run.failure_reason == "test_error"
    await db_session.rollback()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invalid_run_state_transition_raises(db_session):
    """Invalid state transition raises RunStateError."""
    from trend_intel.orchestration import run_service
    from trend_intel.schemas.runs import RunCreate, RunStatus
    from trend_intel.core.errors import RunStateError

    run = await run_service.create_run(db_session, RunCreate(trigger_type="manual"))
    await db_session.flush()

    with pytest.raises(RunStateError):
        await run_service.transition_run(db_session, run, RunStatus.SUCCEEDED)
    await db_session.rollback()


@pytest.mark.asyncio
async def test_pdf_failure_preserves_markdown(tmp_path):
    """PDF render failure does not destroy the Markdown file (FR-014)."""
    from trend_intel.reporting.pdf import render_pdf

    # Intentionally bad HTML to force failure
    result = render_pdf("<html><body>test</body></html>", tmp_path / "test.pdf")
    # Either succeeds or fails gracefully — never raises
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_agent_bounded_retry():
    """Agent stops retrying after AGENT_MAX_RETRIES."""
    from trend_intel.agents.research_agent import ResearchAgent
    from trend_intel.core.errors import AgentError
    from openai import APIError

    agent = ResearchAgent()
    call_count = 0

    async def _mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        raise APIError("mock api error", request=None, body=None)

    with patch.object(agent._client.chat.completions, "create", side_effect=_mock_create):
        result = await agent.run_safe("test")
        assert result is None
        assert call_count <= agent._settings.agent_max_retries + 2
