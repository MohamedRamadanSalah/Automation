from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from trend_intel.db.base import Base


class ScoringMethod(Base):
    __tablename__ = "scoring_methods"

    version: Mapped[str] = mapped_column(String, primary_key=True)  # e.g. "v1"
    weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
