from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from trend_intel.db.base import Base

VALID_ROLES = frozenset(
    {"research", "trend_analysis", "technical_analyst", "comparison", "ranking", "report_writer", "quality_reviewer"}
)


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    role: Mapped[str] = mapped_column(String, primary_key=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)  # null → use shared default
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"), onupdate=datetime.utcnow)
