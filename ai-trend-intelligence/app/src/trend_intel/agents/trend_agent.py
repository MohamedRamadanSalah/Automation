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
        "You are a technology trend analyst. Given research about a tool and its popularity signals, "
        "explain why it is trending right now. Return JSON: "
        "{\"ok\": true, \"data\": {\"trend_rationale\": \"...\", \"drivers\": [...], "
        "\"momentum_assessment\": \"low|moderate|high\", \"evidence\": [...], \"momentum_0_100\": 0-100}}"
    )
