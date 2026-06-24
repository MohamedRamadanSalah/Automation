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
        "You are a technology research analyst. Given a tool name and context, return ONLY a JSON object with these exact keys:\n"
        "{\n"
        '  "summary": "<2-3 sentence description of what the tool does>",\n'
        '  "category": "<one of: AI/ML, DevOps, Frontend, Backend, Security, Data, Developer Tools, Other>",\n'
        '  "key_features": ["feature1", "feature2", "feature3"],\n'
        '  "primary_use_cases": ["use case 1", "use case 2"]\n'
        "}\n"
        "Return ONLY the JSON object. No explanation, no markdown, no wrapper."
    )
