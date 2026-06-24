"""Comparison Agent — compares tool against competitors (FR-007)."""
from __future__ import annotations

from pydantic import BaseModel

from trend_intel.agents.base import BaseAgent


class CompetitorItem(BaseModel):
    name: str
    how_it_compares: str


class ComparisonOutput(BaseModel):
    competitors: list[CompetitorItem]
    differentiation: str
    positioning: str  # leader | challenger | niche | new-entrant
    source_credibility_0_100: float = 60.0


class ComparisonAgent(BaseAgent[ComparisonOutput]):
    role = "comparison"
    output_schema = ComparisonOutput
    system_prompt = (
        "You are a competitive intelligence analyst. Compare a technology tool against its main competitors. "
        "Return JSON: {\"ok\": true, \"data\": {\"competitors\": [{\"name\": \"...\", \"how_it_compares\": \"...\"}], "
        "\"differentiation\": \"...\", \"positioning\": \"leader|challenger|niche|new-entrant\", \"source_credibility_0_100\": 0-100}}"
    )
