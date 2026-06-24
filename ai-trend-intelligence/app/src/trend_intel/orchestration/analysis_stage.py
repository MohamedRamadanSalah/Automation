"""Analysis stage — per-tool Research + basic ranking (T033 MVP)."""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.agents.research_agent import ResearchAgent
from trend_intel.core.logging import get_logger
from trend_intel.core.scoring import SCORING_VERSION, compute_score, popularity_from_signals
from trend_intel.models.candidates import Candidate
from trend_intel.models.tool_profiles import ToolProfile
from trend_intel.models.tools import Tool
from trend_intel.orchestration import run_service
from trend_intel.schemas.runs import RunStatus, StageResult

log = get_logger(__name__)


async def run_analyze(run_id: uuid.UUID, session: AsyncSession) -> StageResult:
    run = await run_service.get_run(session, run_id)
    await run_service.transition_run(session, run, RunStatus.ANALYZING)
    step = await run_service.start_step(session, run_id, "research")
    await session.commit()

    # Get validated tools for this run
    result = await session.execute(
        select(Candidate).where(Candidate.run_id == run_id, Candidate.validation_status == "merged")
    )
    candidates = list(result.scalars())
    tool_ids = list({c.tool_id for c in candidates if c.tool_id})

    config = run.config_snapshot
    top_n: int = config.get("top_n", 15)
    concurrency: int = config.get("agent_concurrency", 3)
    sem = asyncio.Semaphore(concurrency)

    agent = ResearchAgent()
    profiles_created = 0
    analysis_gaps: list[str] = []

    async def _analyze_tool(tool_id: uuid.UUID) -> ToolProfile | None:
        async with sem:
            tool_result = await session.execute(select(Tool).where(Tool.id == tool_id))
            tool = tool_result.scalar_one_or_none()
            if tool is None:
                return None

            # Get candidates for context
            cands = [c for c in candidates if c.tool_id == tool_id]
            signals = {}
            for c in cands:
                signals.update(c.raw_signals or {})

            user_content = json.dumps({
                "tool": {"canonical_name": tool.canonical_name, "url": tool.homepage_url, "source_refs": tool.source_refs, "raw_signals": signals},
                "collected_text": f"Tool: {tool.canonical_name}. URL: {tool.homepage_url}. Trending on: {[c.raw_signals for c in cands[:3]]}"
            })

            research = await agent.run_safe(user_content)
            if research is None:
                analysis_gaps.append(str(tool_id))
                log.warning("research_failed_isolated", tool_id=str(tool_id))
                # Create minimal profile with gaps noted
                pop_score = popularity_from_signals(signals)
                score, components = compute_score(popularity_0_100=pop_score)
                profile = ToolProfile(
                    report_id=uuid.uuid4(),  # placeholder — will be updated at report stage
                    tool_id=tool_id,
                    research_summary="[Analysis unavailable]",
                    trend_rationale="[Analysis unavailable]",
                    score=score,
                    score_components=components,
                    scoring_method_version=SCORING_VERSION,
                    analysis_gaps=["research_agent_failed"],
                )
                return profile

            pop_score = popularity_from_signals(signals)
            tech_merit = 50.0
            score, components = compute_score(
                popularity_0_100=pop_score,
                momentum_0_100=50.0,
                technical_merit_0_100=tech_merit,
                source_credibility_0_100=60.0,
            )

            profile = ToolProfile(
                report_id=uuid.uuid4(),  # placeholder — updated at report stage
                tool_id=tool_id,
                research_summary=research.summary,
                trend_rationale=f"Trending in {research.category}",
                technical_strengths=research.key_features,
                technical_weaknesses=[],
                score=score,
                score_components=components,
                scoring_method_version=SCORING_VERSION,
            )
            return profile

    tool_ids_to_analyze = tool_ids[:top_n]
    results = await asyncio.gather(*[_analyze_tool(tid) for tid in tool_ids_to_analyze])
    profiles = [p for p in results if p is not None]

    # Sort by score descending and store temporarily (report_id set in report stage)
    profiles.sort(key=lambda p: float(p.score), reverse=True)

    # Persist analysis context in run metadata for report stage
    run.config_snapshot = {**run.config_snapshot, "_analysis_profiles": [
        {"tool_id": str(p.tool_id), "score": float(p.score), "summary": p.research_summary,
         "trend_rationale": p.trend_rationale, "strengths": p.technical_strengths,
         "gaps": p.analysis_gaps, "components": p.score_components}
        for p in profiles
    ]}
    profiles_created = len(profiles)

    await run_service.finish_step(session, step, detail={"tools_analyzed": profiles_created, "gaps": len(analysis_gaps)})
    await session.commit()

    return StageResult(run_id=run_id, stage="analyze", status="succeeded", detail={"tools_analyzed": profiles_created})
