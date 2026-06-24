from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from trend_intel.db.base import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_generated_at", "generated_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id"), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # succeeded | partial | failed
    markdown_path: Mapped[str] = mapped_column(String, nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    pdf_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # generated|failed|pending
    sections: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_notes: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
