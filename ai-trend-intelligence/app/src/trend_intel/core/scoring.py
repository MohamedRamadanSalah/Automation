"""Versioned weighted composite scoring (FR-008, R8) — T032 MVP, upgraded in T056."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

# v1 weights (seeded in migration 0001_baseline)
V1_WEIGHTS: dict[str, float] = {
    "popularity": 0.30,
    "momentum": 0.30,
    "technical_merit": 0.25,
    "source_credibility": 0.15,
}
SCORING_VERSION = "v1"


def compute_score(
    popularity_0_100: float = 50.0,
    momentum_0_100: float = 50.0,
    technical_merit_0_100: float = 50.0,
    source_credibility_0_100: float = 50.0,
    weights: dict[str, float] | None = None,
) -> tuple[Decimal, dict[str, Any]]:
    """Return (composite_score, score_components) using versioned weights.

    The composite is computed deterministically in code, not by the LLM (FR-008).
    """
    w = weights or V1_WEIGHTS
    composite = (
        w["popularity"] * popularity_0_100
        + w["momentum"] * momentum_0_100
        + w["technical_merit"] * technical_merit_0_100
        + w["source_credibility"] * source_credibility_0_100
    )
    components = {
        "popularity": {"raw": popularity_0_100, "weight": w["popularity"]},
        "momentum": {"raw": momentum_0_100, "weight": w["momentum"]},
        "technical_merit": {"raw": technical_merit_0_100, "weight": w["technical_merit"]},
        "source_credibility": {"raw": source_credibility_0_100, "weight": w["source_credibility"]},
        "composite": round(composite, 2),
        "version": SCORING_VERSION,
    }
    return Decimal(str(round(composite, 2))), components


# All popularity-like signal keys any discovery source may emit. Kept in ONE place so
# validation (exclusion), analysis (selection), and scoring never disagree on how popular
# a candidate is — a mismatch here silently drops trending items ("too few results").
POPULARITY_SIGNAL_KEYS = ("score", "stars", "upvotes", "points", "reactions", "votes")


def raw_popularity(raw_signals: dict[str, Any] | None) -> float:
    """Return the highest popularity-like signal value as a float (0 if none present)."""
    if not raw_signals:
        return 0.0
    best = 0.0
    for key in POPULARITY_SIGNAL_KEYS:
        val = raw_signals.get(key)
        if isinstance(val, (int, float)):
            best = max(best, float(val))
    return best


def popularity_from_signals(raw_signals: dict[str, Any]) -> float:
    """Convert raw source signals to a 0–100 popularity score (log-normalized)."""
    score = raw_popularity(raw_signals)
    # Log-normalize: 500+ points → ~100, 10 → ~20
    import math
    return min(100.0, max(0.0, math.log1p(score) / math.log1p(500) * 100))
