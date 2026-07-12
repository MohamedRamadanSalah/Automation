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
        "You are a technology ranking analyst. You are given the full analysis of a tool (research, "
        "trend, technical, comparison) plus raw source signals, and you assign four calibrated 0-100 "
        "scores that feed a weighted composite. Be discriminating: use the FULL range, reserve 85+ for "
        "genuinely exceptional cases, and do not cluster everything near 50 or 100.\n\n"
        "DIMENSIONS:\n"
        "- popularity_0_100: current adoption/attention. Anchor on the raw signals (stars, points, "
        "upvotes, reactions). Very high engagement -> high; sparse signals -> low.\n"
        "- momentum_0_100: rate and durability of growth (reuse the trend analysis; 0-33 low, 34-66 "
        "moderate, 67-100 high).\n"
        "- technical_merit_0_100: engineering quality and applicability (reuse the technical analysis).\n"
        "- source_credibility_0_100: trustworthiness of the tool and its signal provenance.\n\n"
        "Keep the scores CONSISTENT with the upstream analysis you were given (do not contradict a "
        "'high momentum' finding with a momentum score of 20). The justification must reference the "
        "main reasons for the scores.\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "{\n"
        '  "popularity_0_100": <integer 0-100>,\n'
        '  "momentum_0_100": <integer 0-100>,\n'
        '  "technical_merit_0_100": <integer 0-100>,\n'
        '  "source_credibility_0_100": <integer 0-100>,\n'
        '  "justification": "<one to two sentences explaining the scores>"\n'
        "}\n"
        "Return ONLY the JSON object. No explanation, no markdown fences, no wrapper."
    )
