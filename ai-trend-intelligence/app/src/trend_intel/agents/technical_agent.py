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
        "You are a senior software engineer evaluating technology tools. "
        "Return ONLY a JSON object with these exact keys:\n"
        "{\n"
        '  "strengths": ["strength1", "strength2", "strength3"],\n'
        '  "weaknesses": ["weakness1", "weakness2"],\n'
        '  "maturity": "<experimental or emerging or established>",\n'
        '  "technical_merit_0_100": <number 0-100>\n'
        "}\n"
        "Return ONLY the JSON object. No explanation, no markdown, no wrapper."
    )
