"""Shared pytest fixtures."""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

# Set test environment before any imports touch config
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("OPENROUTER_API_KEY", "sk-or-test-key")


@pytest.fixture
def mock_db_session(monkeypatch):
    """Replace get_session dependency with a no-op async generator."""
    from trend_intel.db import session as sess_mod

    session_mock = AsyncMock()
    session_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None), scalars=MagicMock(return_value=[])))
    session_mock.flush = AsyncMock()
    session_mock.commit = AsyncMock()
    session_mock.add = MagicMock()

    async def _fake_session():
        yield session_mock

    monkeypatch.setattr(sess_mod, "get_session", _fake_session)
    return session_mock


@pytest_asyncio.fixture
async def db_session():
    """Real async session for integration tests — requires a running PostgreSQL."""
    from trend_intel.db.session import get_session_factory
    factory = get_session_factory()
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def openrouter_mock(respx_mock):
    """Mock OpenRouter completions endpoint."""
    import json
    respx_mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=__import__("httpx").Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "ok": True,
                                "data": {
                                    "summary": "Test tool summary",
                                    "category": "AI",
                                    "key_features": ["feature1"],
                                    "primary_use_cases": ["use case 1"],
                                }
                            })
                        }
                    }
                ]
            },
        )
    )
    return respx_mock
