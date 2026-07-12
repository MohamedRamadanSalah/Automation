"""Analysis stage — per-tool deep analysis with domain-balanced selection."""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.agents.comparison_agent import ComparisonAgent
from trend_intel.agents.ranking_agent import RankingAgent
from trend_intel.agents.research_agent import ResearchAgent
from trend_intel.agents.technical_agent import TechnicalAgent
from trend_intel.agents.trend_agent import TrendAgent
from trend_intel.core.logging import get_logger
from trend_intel.core.scoring import SCORING_VERSION, compute_score, popularity_from_signals, raw_popularity
from trend_intel.models.candidates import Candidate
from trend_intel.models.tool_profiles import ToolProfile
from trend_intel.models.tools import Tool
from trend_intel.orchestration import run_service
from trend_intel.schemas.runs import RunStatus, StageResult

log = get_logger(__name__)

DOMAINS = [
    "ai_engineering",
    "flutter",
    "dotnet",
    "systems_design",
    "software_engineering",
    "job_market",
    "general",
]

DOMAIN_LABELS = {
    "ai_engineering": "AI Engineering",
    "flutter": "Flutter & Mobile",
    "dotnet": ".NET & C#",
    "systems_design": "Systems Design & Architecture",
    "software_engineering": "Software Engineering",
    "job_market": "Job Market & Skills",
    "general": "General Tech",
}


def _infer_domain(canonical_domain: str | None, signals: dict) -> str:
    """Infer category from domain/signals when not explicitly set."""
    cat = signals.get("category")
    if cat and cat in DOMAINS:
        return cat
    domain = (canonical_domain or "").lower()
    if "huggingface" in domain or "langchain" in domain or "deeplearning" in domain:
        return "ai_engineering"
    if "devblogs.microsoft" in domain or "dotnet" in domain:
        return "dotnet"
    if "martinfowler" in domain or "infoq" in domain or "highscalability" in domain:
        return "systems_design"
    if "netflixtechblog" in domain or "engineering." in domain:
        return "software_engineering"
    return "general"


def _candidate_popularity(signals: dict) -> float:
    # Single source of truth shared with validation & scoring (core.scoring.raw_popularity).
    return raw_popularity(signals)


async def run_analyze(run_id: uuid.UUID, session: AsyncSession) -> StageResult:
    run = await run_service.get_run(session, run_id)
    await run_service.transition_run(session, run, RunStatus.ANALYZING)
    step = await run_service.start_step(session, run_id, "research")
    await session.commit()

    # Fetch all validated candidates
    result = await session.execute(
        select(Candidate).where(
            Candidate.run_id == run_id, Candidate.validation_status == "merged"
        )
    )
    candidates = list(result.scalars())

    config = run.config_snapshot
    top_n: int = config.get("top_n", 15)
    concurrency: int = config.get("agent_concurrency", 3)
    sem = asyncio.Semaphore(concurrency)

    # ── Build per-tool metadata ──────────────────────────────────────────────
    tool_info: dict[uuid.UUID, dict] = {}
    for c in candidates:
        tid = c.tool_id
        if tid is None:
            continue
        signals = c.raw_signals or {}
        pop = _candidate_popularity(signals)
        domain = _infer_domain(c.canonical_domain, signals)

        if tid not in tool_info:
            tool_info[tid] = {
                "popularity": pop,
                "domain": domain,
                "url": c.url,
                "raw_name": c.raw_name,
                "canonical_domain": c.canonical_domain,
                "signals": signals,
            }
        else:
            if pop > tool_info[tid]["popularity"]:
                tool_info[tid]["popularity"] = pop
            if domain != "general" and tool_info[tid]["domain"] == "general":
                tool_info[tid]["domain"] = domain

    # ── Domain-balanced selection ────────────────────────────────────────────
    # Goal: represent every domain; fill remaining slots with highest-popularity.
    per_domain = max(3, top_n // len(DOMAINS))

    domain_buckets: dict[str, list[tuple[float, uuid.UUID]]] = {d: [] for d in DOMAINS}
    for tid, info in tool_info.items():
        d = info["domain"] if info["domain"] in DOMAINS else "general"
        domain_buckets[d].append((info["popularity"], tid))
    for d in domain_buckets:
        domain_buckets[d].sort(reverse=True)

    selected: list[uuid.UUID] = []
    selected_set: set[uuid.UUID] = set()
    for d in DOMAINS:
        for _, tid in domain_buckets[d][:per_domain]:
            if tid not in selected_set:
                selected_set.add(tid)
                selected.append(tid)

    # Fill remaining up to top_n from overall popularity ranking
    all_sorted = sorted(tool_info.keys(), key=lambda tid: tool_info[tid]["popularity"], reverse=True)
    for tid in all_sorted:
        if len(selected) >= top_n:
            break
        if tid not in selected_set:
            selected_set.add(tid)
            selected.append(tid)

    tool_ids_to_analyze = selected[:top_n]

    # ── Domain news digest (ALL validated items, not just top_n) ────────────
    domain_news: dict[str, list[dict]] = {d: [] for d in DOMAINS}
    seen_news: set[uuid.UUID] = set()
    for c in candidates:
        tid = c.tool_id
        if tid is None or tid in seen_news:
            continue
        seen_news.add(tid)
        signals = c.raw_signals or {}
        pop = _candidate_popularity(signals)
        domain = _infer_domain(c.canonical_domain, signals)
        bucket = domain if domain in DOMAINS else "general"
        domain_news[bucket].append({
            "name": c.raw_name,
            "url": c.url or "",
            "score": pop,
            "description": signals.get("description", ""),
            "domain": domain,
        })
    for d in domain_news:
        domain_news[d].sort(key=lambda x: x["score"], reverse=True)

    # ── Deep-analysis agents ─────────────────────────────────────────────────
    research_agent = ResearchAgent()
    trend_agent = TrendAgent()
    technical_agent = TechnicalAgent()
    comparison_agent = ComparisonAgent()
    ranking_agent = RankingAgent()
    analysis_gaps: list[str] = []

    async def _analyze_tool(tool_id: uuid.UUID) -> tuple[ToolProfile | None, dict]:
        async with sem:
            tool_result = await session.execute(select(Tool).where(Tool.id == tool_id))
            tool = tool_result.scalar_one_or_none()
            if tool is None:
                return None, {}

            cands = [c for c in candidates if c.tool_id == tool_id]
            signals: dict = {}
            for c in cands:
                signals.update(c.raw_signals or {})

            base_input = json.dumps({
                "tool": {
                    "canonical_name": tool.canonical_name,
                    "url": tool.homepage_url,
                    "source_refs": tool.source_refs,
                    "raw_signals": signals,
                },
                "collected_text": f"Tool: {tool.canonical_name}. URL: {tool.homepage_url}.",
            })

            gaps: list[str] = []
            research = await research_agent.run_safe(base_input)
            if research is None:
                gaps.append("research_agent_failed")

            research_ctx = json.dumps({
                "research": research.model_dump() if research else {},
                "signals": signals,
            })
            trend = await trend_agent.run_safe(research_ctx)
            if trend is None:
                gaps.append("trend_agent_failed")

            technical = await technical_agent.run_safe(
                base_input + f"\nResearch: {research.model_dump() if research else {}}"
            )
            if technical is None:
                gaps.append("technical_agent_failed")

            comparison = await comparison_agent.run_safe(base_input)
            if comparison is None:
                gaps.append("comparison_agent_failed")

            ranking_input = json.dumps({
                "tool": tool.canonical_name,
                "research": research.model_dump() if research else {},
                "trend": trend.model_dump() if trend else {},
                "technical": technical.model_dump() if technical else {},
                "comparison": comparison.model_dump() if comparison else {},
                "signals": signals,
            })
            ranking_out = await ranking_agent.run_safe(ranking_input)

            if ranking_out:
                score, components = compute_score(
                    popularity_0_100=ranking_out.popularity_0_100,
                    momentum_0_100=ranking_out.momentum_0_100,
                    technical_merit_0_100=ranking_out.technical_merit_0_100,
                    source_credibility_0_100=ranking_out.source_credibility_0_100,
                )
            else:
                gaps.append("ranking_agent_failed")
                pop_score = popularity_from_signals(signals)
                score, components = compute_score(popularity_0_100=pop_score)

            if gaps:
                analysis_gaps.extend([f"{tool.canonical_name}:{g}" for g in gaps])

            profile = ToolProfile(
                report_id=uuid.uuid4(),
                tool_id=tool_id,
                research_summary=research.summary if research else "[Analysis unavailable]",
                trend_rationale=trend.trend_rationale if trend else "[Analysis unavailable]",
                technical_strengths=technical.strengths if technical else (
                    research.key_features if research else []
                ),
                technical_weaknesses=technical.weaknesses if technical else [],
                comparison=comparison.model_dump() if comparison else {},
                score=score,
                score_components=components,
                scoring_method_version=SCORING_VERSION,
                analysis_gaps=gaps,
            )
            extra = {
                "category": research.category if research else _infer_domain(
                    tool.homepage_url, signals
                ),
                "key_features": research.key_features if research else [],
                "primary_use_cases": research.primary_use_cases if research else [],
                "drivers": trend.drivers if trend else [],
                "momentum_assessment": trend.momentum_assessment if trend else "",
                "evidence": trend.evidence if trend else [],
                "weaknesses": technical.weaknesses if technical else [],
                "maturity": technical.maturity if technical else "",
                "competitors": [c.model_dump() for c in comparison.competitors] if comparison else [],
                "differentiation": comparison.differentiation if comparison else "",
                "positioning": comparison.positioning if comparison else "",
                "justification": ranking_out.justification if ranking_out else "",
            }
            return profile, extra

    results = await asyncio.gather(
        *[_analyze_tool(tid) for tid in tool_ids_to_analyze]
    )
    pairs = [(p, e) for p, e in results if p is not None]
    profiles = [p for p, _ in pairs]
    extras_by_tid = {str(p.tool_id): e for p, e in pairs}

    profiles.sort(key=lambda p: float(p.score), reverse=True)

    run.config_snapshot = {
        **run.config_snapshot,
        "_analysis_profiles": [
            {
                "tool_id": str(p.tool_id),
                "score": float(p.score),
                "summary": p.research_summary,
                "trend_rationale": p.trend_rationale,
                "strengths": p.technical_strengths,
                "gaps": p.analysis_gaps,
                "components": p.score_components,
                **extras_by_tid.get(str(p.tool_id), {}),
            }
            for p in profiles
        ],
        "_domain_news": domain_news,
        "_domain_labels": DOMAIN_LABELS,
    }
    profiles_created = len(profiles)

    await run_service.finish_step(
        session,
        step,
        detail={"tools_analyzed": profiles_created, "gaps": len(analysis_gaps)},
    )
    await session.commit()

    return StageResult(
        run_id=run_id,
        stage="analyze",
        status="succeeded",
        detail={"tools_analyzed": profiles_created},
    )
