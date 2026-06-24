"""Ranking Agent — supplies per-dimension 0–100 values for the composite (FR-008, R8)."""
from __future__ import annotations

from pydantic import BaseModel

from trend_intel.agents.base import BaseAgent


class RankingOutput(BaseModel):
    popularity_0_100: float
    momentum_0_100: float
    technical_merit_0_100: float
    source_credibility_0_100: float
    justification: str


class RankingAgent(BaseAgent[RankingOutput]):
    role = "ranking"
    output_schema = RankingOutput
    system_prompt = (
        "You are a technology ranking analyst. Given all analysis for a tool (research, trend, technical, comparison), "
        "score each of the four dimensions 0–100: popularity, momentum, technical_merit, source_credibility. "
        "The final composite will be computed by code from these values. Be rigorous and objective. "
        "Return JSON: {\"ok\": true, \"data\": {\"popularity_0_100\": 0-100, \"momentum_0_100\": 0-100, "
        "\"technical_merit_0_100\": 0-100, \"source_credibility_0_100\": 0-100, \"justification\": \"...\"}}"
    )
