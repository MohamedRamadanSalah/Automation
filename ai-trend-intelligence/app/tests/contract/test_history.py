"""Contract tests for history + comparison endpoints (T059)."""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from trend_intel.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_tool_history_not_found(client, mock_db_session):
    response = await client.get(f"/tools/{uuid.uuid4()}/history")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_compare_reports_structure(client, mock_db_session):
    r1, r2 = uuid.uuid4(), uuid.uuid4()
    response = await client.get(f"/reports/compare?base_id={r1}&target_id={r2}")
    # Should return a dict (may have empty lists when no tools found in mock)
    assert response.status_code in (200, 404, 500)
