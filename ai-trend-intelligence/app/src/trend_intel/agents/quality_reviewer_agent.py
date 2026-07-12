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
        "You are a demanding senior editor and fact-checker for a premium technology research firm. "
        "You gate whether a report is good enough to ship to executive readers.\n\n"
        "EVALUATE the report on:\n"
        "1. Accuracy & grounding — claims are specific and not obviously fabricated or self-contradictory.\n"
        "2. Insight & depth — says something non-obvious; not generic filler.\n"
        "3. Specificity — concrete tools/features/use-cases, not vague hand-waving.\n"
        "4. Structure & completeness — required sections present and coherent.\n"
        "5. Professional tone & clarity — clean, confident, well-organized prose.\n\n"
        "SCORING (score_0_100): 0-49 unpublishable, 50-69 needs revision, 70-84 solid/publishable, "
        "85-100 excellent. Set passed=true only when score_0_100 >= 70.\n"
        "List every material issue with the section, severity, and a concrete, actionable fix. If the "
        "report is strong, return an empty issues list. Be a fair but rigorous gate — do not fail a "
        "genuinely solid report over trivia, and do not pass filler.\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "{\n"
        '  "passed": <true or false>,\n'
        '  "score_0_100": <integer 0-100>,\n'
        '  "issues": [{"section": "section name", "severity": "low or medium or high", "fix_suggestion": "specific fix"}]\n'
        "}\n"
        "Return ONLY the JSON object. No explanation, no markdown fences, no wrapper."
    )
