from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RunStatus:
    PENDING = "pending"
    DISCOVERING = "discovering"
    VALIDATING = "validating"
    ANALYZING = "analyzing"
    REPORTING = "reporting"
    EXPORTING = "exporting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NO_TRENDS = "no_trends"


class RunCreate(BaseModel):
    trigger_type: str = Field("manual", pattern="^(manual|scheduled)$")
    config_override: dict[str, Any] = Field(default_factory=dict)


class Run(BaseModel):
    id: uuid.UUID
    trigger_type: str
    status: str
    outcome: str | None
    report_id: uuid.UUID | None
    skipped_sources: list[str]
    failure_reason: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RunStep(BaseModel):
    id: uuid.UUID
    step: str
    status: str
    attempts: int
    detail: dict[str, Any]
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class RunDetail(Run):
    steps: list[RunStep] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class StageResult(BaseModel):
    run_id: uuid.UUID
    stage: str
    status: str
    detail: dict[str, Any] = Field(default_factory=dict)
