from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal

from trend_intel.db.base import Base


class ToolProfile(Base):
    __tablename__ = "tool_profiles"
    __table_args__ = (
        UniqueConstraint("report_id", "tool_id", name="uq_tool_profiles_report_tool"),
        Index("ix_tool_profiles_tool_id", "tool_id"),
        Index("ix_tool_profiles_report_id", "report_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False)
    tool_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tools.id"), nullable=False)
    research_summary: Mapped[str] = mapped_column(Text, nullable=False)
    trend_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    technical_strengths: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    technical_weaknesses: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    comparison: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    score_components: Mapped[dict] = mapped_column(JSONB, nullable=False)
    scoring_method_version: Mapped[str] = mapped_column(String, ForeignKey("scoring_methods.version"), nullable=False)
    analysis_gaps: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
