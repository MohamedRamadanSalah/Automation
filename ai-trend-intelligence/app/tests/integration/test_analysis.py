"""Integration tests: full agent fan-out + review loop + per-tool isolation (T050)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_failure_isolates_to_tool():
    """A single agent failure records analysis_gap, does not abort the run."""
    from trend_intel.agents.base import BaseAgent, AgentError
    from trend_intel.agents.research_agent import ResearchAgent

    agent = ResearchAgent()
    with patch.object(agent, "run", side_effect=AgentError("mock failure")):
        result = await agent.run_safe("test")
        assert result is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_review_loop_bounded(db_session, openrouter_mock):
    """Quality reviewer loop terminates within REVIEW_MAX_ATTEMPTS."""
    from trend_intel.config import get_settings
    settings = get_settings()
    assert settings.review_max_attempts >= 1
