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
        "You are a competitive intelligence analyst comparing technology tools. "
        "Return ONLY a JSON object with these exact keys:\n"
        "{\n"
        '  "competitors": [{"name": "Tool A", "how_it_compares": "description"}],\n'
        '  "differentiation": "<what makes this tool unique>",\n'
        '  "positioning": "<leader or challenger or niche or new-entrant>",\n'
        '  "source_credibility_0_100": <number 0-100>\n'
        "}\n"
        "Return ONLY the JSON object. No explanation, no markdown, no wrapper."
    )
