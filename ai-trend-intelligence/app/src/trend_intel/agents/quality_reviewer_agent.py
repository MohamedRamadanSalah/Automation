"""Quality Reviewer Agent — drives the bounded revise→re-review loop (FR-010)."""
from __future__ import annotations

from pydantic import BaseModel

from trend_intel.agents.base import BaseAgent


class QualityIssue(BaseModel):
    section: str
    severity: str  # low | medium | high
    fix_suggestion: str


class QualityOutput(BaseModel):
    passed: bool
    score_0_100: int
    issues: list[QualityIssue]


class QualityReviewerAgent(BaseAgent[QualityOutput]):
    role = "quality_reviewer"
    output_schema = QualityOutput
    system_prompt = (
        "You are a senior editor reviewing a technology research report. Evaluate the draft for accuracy, "
        "completeness, coherence, and professional quality. Score 0–100 and list any issues with sections and fix suggestions. "
        "A score >= 70 means passed. "
        "Return JSON: {\"ok\": true, \"data\": {\"passed\": true/false, \"score_0_100\": 0-100, "
        "\"issues\": [{\"section\": \"...\", \"severity\": \"low|medium|high\", \"fix_suggestion\": \"...\"}]}}"
    )
