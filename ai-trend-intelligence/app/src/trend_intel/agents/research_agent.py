"""Research Agent — summarizes what a tool is (FR-007)."""
from __future__ import annotations

from pydantic import BaseModel

from trend_intel.agents.base import BaseAgent


class ResearchOutput(BaseModel):
    summary: str
    category: str
    key_features: list[str]
    primary_use_cases: list[str]


class ResearchAgent(BaseAgent[ResearchOutput]):
    role = "research"
    output_schema = ResearchOutput
    system_prompt = (
        "You are a technology research analyst. Given a tool name, its URL, and any source signals, "
        "research the tool and return a JSON object with: summary (≤200 words), category (e.g. AI/ML, DevOps, Frontend), "
        "key_features (list of strings), primary_use_cases (list of strings). "
        "Always return: {\"ok\": true, \"data\": {\"summary\": \"...\", \"category\": \"...\", \"key_features\": [...], \"primary_use_cases\": [...]}}"
    )
