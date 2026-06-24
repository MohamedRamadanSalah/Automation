"""Contract tests for POST /runs and GET /runs/{id}."""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from trend_intel.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_create_run_manual(client, mock_db_session):
    response = await client.post("/runs", json={"trigger_type": "manual"})
    assert response.status_code == 201
    data = response.json()
    assert data["trigger_type"] == "manual"
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_run_scheduled(client, mock_db_session):
    response = await client.post("/runs", json={"trigger_type": "scheduled"})
    assert response.status_code == 201
    assert response.json()["trigger_type"] == "scheduled"


@pytest.mark.asyncio
async def test_get_run_not_found(client, mock_db_session):
    import uuid
    response = await client.get(f"/runs/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_runs(client, mock_db_session):
    response = await client.get("/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
