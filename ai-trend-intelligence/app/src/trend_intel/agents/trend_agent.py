"""Trend Analysis Agent — explains why a tool is trending (FR-007)."""
from __future__ import annotations

from pydantic import BaseModel

from trend_intel.agents.base import BaseAgent


class TrendOutput(BaseModel):
    trend_rationale: str
    drivers: list[str]
    momentum_assessment: str  # low | moderate | high
    evidence: list[str]
    momentum_0_100: float = 50.0


class TrendAgent(BaseAgent[TrendOutput]):
    role = "trend_analysis"
    output_schema = TrendOutput
    system_prompt = (
        "You are a technology trend analyst. Given a tool name and its source signals, explain why it is trending. "
        "Return ONLY a JSON object with these exact keys:\n"
        "{\n"
        '  "trend_rationale": "<1-2 sentence explanation of why it is trending>",\n'
        '  "drivers": ["driver1", "driver2"],\n'
        '  "momentum_assessment": "<low or moderate or high>",\n'
        '  "evidence": ["evidence point 1", "evidence point 2"],\n'
        '  "momentum_0_100": <number 0-100>\n'
        "}\n"
        "Return ONLY the JSON object. No explanation, no markdown, no wrapper."
    )
