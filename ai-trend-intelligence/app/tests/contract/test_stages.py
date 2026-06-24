"""Contract tests for stage endpoints."""
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
async def test_discover_unknown_run(client, mock_db_session):
    response = await client.post(f"/runs/{uuid.uuid4()}/discover")
    assert response.status_code in (404, 409)


@pytest.mark.asyncio
async def test_validate_unknown_run(client, mock_db_session):
    response = await client.post(f"/runs/{uuid.uuid4()}/validate")
    assert response.status_code in (404, 409)


@pytest.mark.asyncio
async def test_analyze_unknown_run(client, mock_db_session):
    response = await client.post(f"/runs/{uuid.uuid4()}/analyze")
    assert response.status_code in (404, 409)


@pytest.mark.asyncio
async def test_report_unknown_run(client, mock_db_session):
    response = await client.post(f"/runs/{uuid.uuid4()}/report")
    assert response.status_code in (404, 409)
