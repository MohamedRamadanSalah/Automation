"""Validation stage coordinator (T029)."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.core.logging import get_logger
from trend_intel.orchestration import run_service
from trend_intel.schemas.runs import RunStatus, StageResult
from trend_intel.validation.service import validate_candidates

log = get_logger(__name__)


async def run_validate(run_id: uuid.UUID, session: AsyncSession) -> StageResult:
    run = await run_service.get_run(session, run_id)
    await run_service.transition_run(session, run, RunStatus.VALIDATING)
    step = await run_service.start_step(session, run_id, "validation")
    await session.commit()

    tools, excluded = await validate_candidates(session, run_id, run.config_snapshot)

    if not tools:
        await run_service.finish_step(session, step, detail={"validated": 0, "excluded": len(excluded)})
        await run_service.transition_run(session, run, RunStatus.NO_TRENDS, outcome="no_trends")
        await session.commit()
        return StageResult(run_id=run_id, stage="validate", status="no_trends", detail={"validated": 0})

    await run_service.finish_step(session, step, detail={"validated": len(tools), "excluded": len(excluded)})
    await session.commit()

    return StageResult(run_id=run_id, stage="validate", status="succeeded", detail={"validated": len(tools), "excluded": len(excluded)})
