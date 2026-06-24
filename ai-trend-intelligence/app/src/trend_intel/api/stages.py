"""Stage endpoints — thin HTTP layer; logic lives in service modules."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.core.security import require_api_key
from trend_intel.db.session import get_session
from trend_intel.schemas.runs import StageResult

router = APIRouter(tags=["stages"], dependencies=[Depends(require_api_key)])

# Stage implementations are added as US1 progresses (T028, T029, T033, T036)


@router.post("/runs/{run_id}/discover", response_model=StageResult, status_code=status.HTTP_202_ACCEPTED)
async def discover(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> StageResult:
    from trend_intel.orchestration.discovery_stage import run_discover
    return await run_discover(run_id, session)


@router.post("/runs/{run_id}/validate", response_model=StageResult, status_code=status.HTTP_202_ACCEPTED)
async def validate(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> StageResult:
    from trend_intel.orchestration.validation_stage import run_validate
    return await run_validate(run_id, session)


@router.post("/runs/{run_id}/analyze", response_model=StageResult, status_code=status.HTTP_202_ACCEPTED)
async def analyze(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> StageResult:
    from trend_intel.orchestration.analysis_stage import run_analyze
    return await run_analyze(run_id, session)


@router.post("/runs/{run_id}/report", response_model=StageResult, status_code=status.HTTP_202_ACCEPTED)
async def report(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> StageResult:
    from trend_intel.orchestration.report_stage import run_report
    return await run_report(run_id, session)
