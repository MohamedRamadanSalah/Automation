"""Historical intelligence queries (FR-019, FR-020) — implemented fully in T061/T062."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.core.errors import NotFoundError
from trend_intel.models.tool_profiles import ToolProfile
from trend_intel.models.tools import Tool
from trend_intel.models.reports import Report
from trend_intel.models.rankings import Ranking


async def get_tool_history(session: AsyncSession, tool_id: uuid.UUID) -> dict:
    result = await session.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if tool is None:
        raise NotFoundError(f"Tool {tool_id} not found")

    profiles_result = await session.execute(
        select(ToolProfile).where(ToolProfile.tool_id == tool_id).order_by(ToolProfile.created_at.desc())
    )
    appearances = [
        {"report_id": str(p.report_id), "score": float(p.score), "created_at": p.created_at.isoformat()}
        for p in profiles_result.scalars()
    ]
    return {"tool_id": str(tool_id), "canonical_name": tool.canonical_name, "first_seen_at": tool.first_seen_at.isoformat(), "appearances": appearances}


async def compare_reports(session: AsyncSession, base_id: uuid.UUID, target_id: uuid.UUID) -> dict:
    async def _tool_ids(report_id: uuid.UUID) -> dict[str, float]:
        result = await session.execute(select(ToolProfile).where(ToolProfile.report_id == report_id))
        return {str(p.tool_id): float(p.score) for p in result.scalars()}

    base_tools = await _tool_ids(base_id)
    target_tools = await _tool_ids(target_id)

    base_set = set(base_tools)
    target_set = set(target_tools)

    new_tools = list(target_set - base_set)
    dropped_tools = list(base_set - target_set)
    rank_changes = [
        {"tool_id": tid, "base_score": base_tools[tid], "target_score": target_tools[tid], "delta": round(target_tools[tid] - base_tools[tid], 2)}
        for tid in base_set & target_set
        if abs(target_tools[tid] - base_tools[tid]) > 0.5
    ]
    return {"base_id": str(base_id), "target_id": str(target_id), "new_tools": new_tools, "dropped_tools": dropped_tools, "rank_changes": rank_changes}
