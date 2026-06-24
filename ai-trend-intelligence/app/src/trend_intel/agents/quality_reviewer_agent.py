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
        "You are a senior editor reviewing a technology research report. "
        "Score the report 0-100. A score >= 70 means it passed. List any issues found. "
        "Return ONLY a JSON object with these exact keys:\n"
        "{\n"
        '  "passed": <true or false>,\n'
        '  "score_0_100": <number 0-100>,\n'
        '  "issues": [{"section": "section name", "severity": "low or medium or high", "fix_suggestion": "what to fix"}]\n'
        "}\n"
        "Return ONLY the JSON object. No explanation, no markdown, no wrapper."
    )
