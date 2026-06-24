"""Runs CRUD endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.core.security import require_api_key
from trend_intel.db.session import get_session
from trend_intel.models.run_steps import RunStep as RunStepModel
from trend_intel.models.runs import Run as RunModel
from trend_intel.orchestration import run_service
from trend_intel.schemas.runs import Run, RunCreate, RunDetail, RunStep

router = APIRouter(tags=["runs"])


@router.post("/runs", response_model=Run, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
async def create_run(payload: RunCreate = RunCreate(), session: AsyncSession = Depends(get_session)) -> Run:
    run = await run_service.create_run(session, payload)
    await session.commit()
    return Run.model_validate(run)


@router.get("/runs", response_model=list[Run])
async def list_runs(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    session: AsyncSession = Depends(get_session),
) -> list[Run]:
    q = select(RunModel).order_by(RunModel.created_at.desc()).limit(limit)
    if status_filter:
        q = q.where(RunModel.status == status_filter)
    result = await session.execute(q)
    return [Run.model_validate(r) for r in result.scalars()]


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> RunDetail:
    run = await run_service.get_run(session, run_id)
    steps_result = await session.execute(select(RunStepModel).where(RunStepModel.run_id == run_id))
    steps = [RunStep.model_validate(s) for s in steps_result.scalars()]
    detail = RunDetail.model_validate(run)
    detail.steps = steps
    return detail
