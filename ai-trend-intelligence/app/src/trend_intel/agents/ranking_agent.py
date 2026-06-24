"""Ranking Agent — supplies per-dimension 0-100 values for the composite (FR-008, R8)."""
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
        "You are a technology ranking analyst. Score a tool across four dimensions based on all available analysis. "
        "Return ONLY a JSON object with these exact keys:\n"
        "{\n"
        '  "popularity_0_100": <number 0-100>,\n'
        '  "momentum_0_100": <number 0-100>,\n'
        '  "technical_merit_0_100": <number 0-100>,\n'
        '  "source_credibility_0_100": <number 0-100>,\n'
        '  "justification": "<one sentence explaining the scores>"\n'
        "}\n"
        "Return ONLY the JSON object. No explanation, no markdown, no wrapper."
    )
