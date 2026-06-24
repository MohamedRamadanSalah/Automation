from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from trend_intel.db.base import Base


class Ranking(Base):
    __tablename__ = "rankings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reports.id"), unique=True, nullable=False)
    scoring_method_version: Mapped[str] = mapped_column(String, ForeignKey("scoring_methods.version"), nullable=False)
    ordered_entries: Mapped[list] = mapped_column(JSONB, nullable=False)  # [{rank, tool_id, score}]
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
