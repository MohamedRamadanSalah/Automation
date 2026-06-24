"""Assemble ordered Markdown report from sections (T035)."""
from __future__ import annotations

from datetime import datetime


SECTION_ORDER = [
    "cover",
    "executive_summary",
    "table_of_contents",
    "trend_analysis",
    "tool_profiles",
    "rankings",
    "recommendations",
    "conclusions",
]


def assemble_markdown(
    *,
    title: str,
    generated_at: datetime,
    run_id: str,
    executive_summary: str,
    trend_analysis: str,
    tool_profiles_md: str,
    rankings_md: str,
    recommendations: str,
    conclusions: str,
    tool_count: int,
    source_count: int,
) -> tuple[str, list[str]]:
    """Assemble the full Markdown document in required section order.

    Returns (markdown_text, sections_list) where sections_list is the ordered list
    of included section identifiers (for reports.sections validation, FR-013).
    """
    ts = generated_at.strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []

    # 1. Cover (Markdown representation)
    lines += [
        f"# {title}",
        "",
        f"**Generated**: {ts}  ",
        f"**Run ID**: `{run_id}`  ",
        f"**Tools Analyzed**: {tool_count}  ",
        f"**Data Sources**: {source_count}",
        "",
        "---",
        "",
    ]

    # 2. Executive Summary
    lines += ["## Executive Summary", "", executive_summary, "", "---", ""]

    # 3. Table of Contents
    lines += [
        "## Table of Contents",
        "",
        "1. [Executive Summary](#executive-summary)",
        "2. [Trend Analysis](#trend-analysis)",
        "3. [Tool Profiles](#tool-profiles)",
        "4. [Rankings](#rankings)",
        "5. [Recommendations](#recommendations)",
        "6. [Conclusions](#conclusions)",
        "",
        "---",
        "",
    ]

    # 4. Trend Analysis
    lines += ["## Trend Analysis", "", trend_analysis, "", "---", ""]

    # 5. Tool Profiles
    lines += ["## Tool Profiles", "", tool_profiles_md, "", "---", ""]

    # 6. Rankings
    lines += ["## Rankings", "", rankings_md, "", "---", ""]

    # 7. Recommendations
    lines += ["## Recommendations", "", recommendations, "", "---", ""]

    # 8. Conclusions
    lines += ["## Conclusions", "", conclusions, ""]

    return "\n".join(lines), SECTION_ORDER
