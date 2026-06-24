"""History & comparison endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.db.session import get_session

router = APIRouter(tags=["tools"])


@router.get("/tools/{tool_id}/history", response_model=dict)
async def tool_history(tool_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    from trend_intel.history.service import get_tool_history
    return await get_tool_history(session, tool_id)


@router.get("/reports/compare", response_model=dict)
async def compare_reports(
    base_id: uuid.UUID = Query(...),
    target_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from trend_intel.history.service import compare_reports
    return await compare_reports(session, base_id, target_id)
