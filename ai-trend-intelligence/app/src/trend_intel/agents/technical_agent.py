"""Technical Analyst Agent — evaluates strengths and weaknesses (FR-007)."""
from __future__ import annotations

from pydantic import BaseModel

from trend_intel.agents.base import BaseAgent


class TechnicalOutput(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    maturity: str  # experimental | emerging | established
    technical_merit_0_100: float


class TechnicalAgent(BaseAgent[TechnicalOutput]):
    role = "technical_analyst"
    output_schema = TechnicalOutput
    system_prompt = (
        "You are a senior software engineer. Evaluate a technology tool's technical strengths and weaknesses. "
        "Return JSON: {\"ok\": true, \"data\": {\"strengths\": [...], \"weaknesses\": [...], "
        "\"maturity\": \"experimental|emerging|established\", \"technical_merit_0_100\": 0-100}}"
    )
