"""Config endpoints for agent roles and discovery sources."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.core.security import require_api_key
from trend_intel.db.session import get_session

router = APIRouter(tags=["config"])


@router.get("/config/agents", response_model=list[dict])
async def list_agent_configs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    from sqlalchemy import select
    from trend_intel.models.agent_configs import AgentConfig
    result = await session.execute(select(AgentConfig))
    return [{"role": r.role, "model": r.model, "params": r.params} for r in result.scalars()]


@router.put("/config/agents", response_model=dict, dependencies=[Depends(require_api_key)])
async def update_agent_config(payload: dict, session: AsyncSession = Depends(get_session)) -> dict:
    from trend_intel.models.agent_configs import AgentConfig
    role = payload.get("role")
    result = await session.execute(__import__("sqlalchemy").select(AgentConfig).where(AgentConfig.role == role))
    ac = result.scalar_one_or_none()
    if ac is None:
        ac = AgentConfig(role=role)
        session.add(ac)
    if "model" in payload:
        ac.model = payload["model"]
    if "params" in payload:
        ac.params = payload["params"]
    await session.commit()
    return {"role": ac.role, "model": ac.model, "params": ac.params}


@router.get("/config/sources", response_model=list[dict])
async def list_sources(session: AsyncSession = Depends(get_session)) -> list[dict]:
    from sqlalchemy import select
    from trend_intel.models.discovery_sources import DiscoverySource
    result = await session.execute(select(DiscoverySource))
    return [{"id": str(s.id), "key": s.key, "type": s.type, "display_name": s.display_name, "enabled": s.enabled} for s in result.scalars()]


@router.post("/config/sources", response_model=dict, dependencies=[Depends(require_api_key)])
async def create_source(payload: dict, session: AsyncSession = Depends(get_session)) -> dict:
    from trend_intel.models.discovery_sources import DiscoverySource
    source = DiscoverySource(**{k: v for k, v in payload.items() if k in ("key", "type", "display_name", "enabled", "config")})
    session.add(source)
    await session.commit()
    return {"id": str(source.id), "key": source.key, "enabled": source.enabled}
