"""Contract tests for config endpoints (T064)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from trend_intel.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_list_agent_configs(client, mock_db_session):
    response = await client.get("/config/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_sources(client, mock_db_session):
    response = await client.get("/config/sources")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
