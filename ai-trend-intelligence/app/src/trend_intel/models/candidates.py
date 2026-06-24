from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from trend_intel.db.base import Base


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        Index("ix_candidates_run_id", "run_id"),
        Index("ix_candidates_normalized_name", "normalized_name"),
        Index("ix_candidates_tool_id", "tool_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("discovery_sources.id"), nullable=False)
    raw_name: Mapped[str] = mapped_column(String, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    canonical_domain: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_signals: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    discovered_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    tool_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tools.id"), nullable=True)
    validation_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending|merged|excluded
    exclusion_reason: Mapped[str | None] = mapped_column(String, nullable=True)
