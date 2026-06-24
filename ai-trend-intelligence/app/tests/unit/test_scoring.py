"""Unit tests for 4-dimension weighted composite scoring (T049)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from trend_intel.core.scoring import SCORING_VERSION, V1_WEIGHTS, compute_score


def test_compute_score_basic():
    score, components = compute_score(50, 50, 50, 50)
    assert isinstance(score, Decimal)
    expected = round(50 * 0.30 + 50 * 0.30 + 50 * 0.25 + 50 * 0.15, 2)
    assert float(score) == expected


def test_compute_score_weights_sum_to_one():
    total = sum(V1_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9


def test_compute_score_version_tag():
    _, components = compute_score()
    assert components["version"] == SCORING_VERSION


def test_compute_score_max():
    score, _ = compute_score(100, 100, 100, 100)
    assert float(score) == 100.0


def test_compute_score_min():
    score, _ = compute_score(0, 0, 0, 0)
    assert float(score) == 0.0


def test_compute_score_components_structure():
    _, components = compute_score(70, 60, 80, 90)
    for dim in ("popularity", "momentum", "technical_merit", "source_credibility"):
        assert dim in components
        assert "raw" in components[dim]
        assert "weight" in components[dim]
    assert "composite" in components
