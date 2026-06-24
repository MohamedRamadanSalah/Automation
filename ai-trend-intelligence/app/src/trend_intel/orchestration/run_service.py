"""Run lifecycle service — state transitions, step tracking (FR-017, SC-013)."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.core.errors import NotFoundError, RunStateError
from trend_intel.core.logging import get_logger
from trend_intel.core.utils import utcnow
from trend_intel.models.run_steps import RunStep
from trend_intel.models.runs import Run
from trend_intel.schemas.runs import RunCreate, RunStatus

log = get_logger(__name__)

_VALID_TRANSITIONS: dict[str, set[str]] = {
    RunStatus.PENDING: {RunStatus.DISCOVERING, RunStatus.FAILED},
    RunStatus.DISCOVERING: {RunStatus.VALIDATING, RunStatus.FAILED},
    RunStatus.VALIDATING: {RunStatus.ANALYZING, RunStatus.FAILED, RunStatus.NO_TRENDS},
    RunStatus.ANALYZING: {RunStatus.REPORTING, RunStatus.FAILED},
    RunStatus.REPORTING: {RunStatus.EXPORTING, RunStatus.FAILED},
    RunStatus.EXPORTING: {RunStatus.SUCCEEDED, RunStatus.FAILED},
    RunStatus.SUCCEEDED: set(),
    RunStatus.FAILED: set(),
    RunStatus.NO_TRENDS: set(),
}

TERMINAL_STATUSES = {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.NO_TRENDS}


async def create_run(session: AsyncSession, payload: RunCreate) -> Run:
    from trend_intel.config import get_settings

    settings = get_settings()
    snapshot = {
        "top_n": settings.top_n,
        "popularity_threshold": settings.popularity_threshold,
        "agent_concurrency": settings.agent_concurrency,
        "review_max_attempts": settings.review_max_attempts,
        "openrouter_default_model": settings.openrouter_default_model,
        **payload.config_override,
    }
    run = Run(trigger_type=payload.trigger_type, status=RunStatus.PENDING, config_snapshot=snapshot)
    session.add(run)
    await session.flush()
    log.info("run_created", run_id=str(run.id), trigger=run.trigger_type)
    return run


async def get_run(session: AsyncSession, run_id: uuid.UUID) -> Run:
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise NotFoundError(f"Run {run_id} not found")
    return run


async def transition_run(session: AsyncSession, run: Run, new_status: str, *, failure_reason: str | None = None, outcome: str | None = None) -> Run:
    allowed = _VALID_TRANSITIONS.get(run.status, set())
    if new_status not in allowed:
        raise RunStateError(f"Cannot transition run from '{run.status}' to '{new_status}'")
    run.status = new_status
    now = utcnow()
    if new_status == RunStatus.DISCOVERING:
        run.started_at = now
    if new_status in TERMINAL_STATUSES:
        run.finished_at = now
    if failure_reason:
        run.failure_reason = failure_reason
    if outcome:
        run.outcome = outcome
    await session.flush()
    log.info("run_transition", run_id=str(run.id), status=new_status)
    return run


async def start_step(session: AsyncSession, run_id: uuid.UUID, step: str) -> RunStep:
    rs = RunStep(run_id=run_id, step=step, status="running", started_at=utcnow())
    session.add(rs)
    await session.flush()
    return rs


async def finish_step(session: AsyncSession, run_step: RunStep, *, detail: dict[str, Any] | None = None) -> RunStep:
    run_step.status = "succeeded"
    run_step.finished_at = utcnow()
    if detail:
        run_step.detail = detail
    await session.flush()
    return run_step


async def fail_step(session: AsyncSession, run_step: RunStep, error_message: str, *, detail: dict[str, Any] | None = None) -> RunStep:
    run_step.status = "failed"
    run_step.finished_at = utcnow()
    run_step.detail = {**(detail or {}), "error": error_message}
    await session.flush()
    return run_step
