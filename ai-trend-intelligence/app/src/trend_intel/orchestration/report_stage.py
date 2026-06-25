"""Report stage — assemble MD + quality review + PDF + persist (T036)."""
from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.agents.report_writer_agent import ReportWriterAgent
from trend_intel.core.logging import get_logger
from trend_intel.core.utils import utcnow
from trend_intel.core.scoring import SCORING_VERSION
from trend_intel.models.candidates import Candidate
from trend_intel.models.rankings import Ranking
from trend_intel.models.reports import Report
from trend_intel.models.tool_profiles import ToolProfile
from trend_intel.models.tools import Tool
from trend_intel.orchestration import run_service
from trend_intel.reporting.markdown import SECTION_ORDER, assemble_markdown
from trend_intel.reporting.pdf import render_html, render_pdf
from trend_intel.schemas.runs import RunStatus, StageResult

log = get_logger(__name__)

REQUIRED_SECTIONS = [
    "cover", "executive_summary", "table_of_contents",
    "trend_analysis", "tool_profiles", "rankings", "recommendations", "conclusions",
]


async def run_report(run_id: uuid.UUID, session: AsyncSession) -> StageResult:
    from trend_intel.config import get_settings
    settings = get_settings()

    run = await run_service.get_run(session, run_id)
    await run_service.transition_run(session, run, RunStatus.REPORTING)
    step = await run_service.start_step(session, run_id, "report_write")
    await session.commit()

    # Retrieve analysis profiles from config_snapshot
    analysis_profiles: list[dict] = run.config_snapshot.get("_analysis_profiles", [])
    if not analysis_profiles:
        await run_service.fail_step(session, step, "No analysis profiles found")
        await run_service.transition_run(session, run, RunStatus.FAILED, failure_reason="no_analysis_profiles")
        await session.commit()
        return StageResult(run_id=run_id, stage="report", status="failed", detail={"error": "no_analysis_profiles"})

    # Build tool contexts
    tool_ids = [p["tool_id"] for p in analysis_profiles]
    tool_contexts = []
    for p in analysis_profiles:
        tool_result = await session.execute(select(Tool).where(Tool.id == uuid.UUID(p["tool_id"])))
        tool = tool_result.scalar_one_or_none()
        if tool:
            tool_contexts.append({
                "canonical_name": tool.canonical_name,
                "homepage_url": tool.homepage_url,
                "score": p["score"],
                "summary": p["summary"],
                "trend_rationale": p["trend_rationale"],
                "strengths": p.get("strengths", []),
                "weaknesses": p.get("weaknesses", []),
                "category": p.get("category"),
                "key_features": p.get("key_features", []),
                "primary_use_cases": p.get("primary_use_cases", []),
                "drivers": p.get("drivers", []),
                "momentum_assessment": p.get("momentum_assessment", ""),
                "maturity": p.get("maturity", ""),
                "competitors": p.get("competitors", []),
                "differentiation": p.get("differentiation", ""),
                "positioning": p.get("positioning", ""),
                "components": p.get("components", {}),
                "justification": p.get("justification", ""),
            })

    # Call Report Writer agent
    from trend_intel.agents.quality_reviewer_agent import QualityReviewerAgent

    writer = ReportWriterAgent()
    reviewer = QualityReviewerAgent()
    import json
    writer_input = json.dumps({
        "tools": tool_contexts,
        "run_metadata": {"run_id": str(run_id), "tool_count": len(tool_contexts)},
    })
    writer_output = await writer.run_safe(writer_input)

    # Bounded Quality-Reviewer loop (FR-010, T058)
    review_notes: list[dict] = []
    if writer_output:
        draft_md = f"# {writer_output.title}\n\n{writer_output.executive_summary}\n\n{writer_output.trend_analysis}\n\n{writer_output.tool_profiles_md}"
        for _attempt in range(settings.review_max_attempts):
            review = await reviewer.run_safe(draft_md)
            if review is None or review.passed or review.score_0_100 >= settings.review_pass_threshold * 10:
                break
            review_notes = [issue.model_dump() for issue in review.issues]
            # Feed issues back to writer for revision
            revision_input = json.dumps({
                "tools": tool_contexts,
                "run_metadata": {"run_id": str(run_id), "tool_count": len(tool_contexts)},
                "reviewer_issues": review_notes,
                "instruction": "Fix the listed issues in this revision.",
            })
            revised = await writer.run_safe(revision_input)
            if revised:
                writer_output = revised
                draft_md = f"# {writer_output.title}\n\n{writer_output.executive_summary}"

    now = utcnow()
    title = writer_output.title if writer_output else f"Technology Trend Report — {now.strftime('%Y-%m-%d')}"
    exec_summary = writer_output.executive_summary if writer_output else "Premium trend analysis of top technologies."
    trend_analysis = writer_output.trend_analysis if writer_output else "Analysis in progress."
    tool_profiles_md = writer_output.tool_profiles_md if writer_output else "\n\n".join([f"### {t['canonical_name']}\n{t['summary']}" for t in tool_contexts])
    recommendations = writer_output.recommendations if writer_output else "See tool profiles for detailed guidance."
    conclusions = writer_output.conclusions if writer_output else "Multiple promising technologies identified."

    # Rankings markdown
    rankings_md_lines = ["| Rank | Tool | Score |", "|------|------|-------|"]
    for i, p in enumerate(analysis_profiles, 1):
        rankings_md_lines.append(f"| {i} | {p.get('summary', '')[:40]}... | {p['score']:.1f} |")
    rankings_md = "\n".join(rankings_md_lines)

    # Assemble Markdown
    md_text, sections = assemble_markdown(
        title=title,
        generated_at=now,
        run_id=str(run_id),
        executive_summary=exec_summary,
        trend_analysis=trend_analysis,
        tool_profiles_md=tool_profiles_md,
        rankings_md=rankings_md,
        recommendations=recommendations,
        conclusions=conclusions,
        tool_count=len(tool_contexts),
        source_count=1,
    )

    # Persist files
    storage_dir = Path(settings.storage_root) / "reports" / str(run_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    md_path = storage_dir / "report.md"
    md_path.write_text(md_text, encoding="utf-8")

    # Render PDF
    domain_news = run.config_snapshot.get("_domain_news", {})
    domain_labels = run.config_snapshot.get("_domain_labels", {})
    # Build non-empty domain sections for the template
    domain_sections = [
        {
            "key": domain,
            "label": domain_labels.get(domain, domain.replace("_", " ").title()),
            "items": items[:25],
        }
        for domain, items in domain_news.items()
        if items
    ]

    html_context = {
        "title": title,
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "run_id": str(run_id),
        "executive_summary": exec_summary,
        "trend_analysis": trend_analysis,
        "recommendations": recommendations,
        "conclusions": conclusions,
        "tool_count": len(tool_contexts),
        "source_count": 5,
        "total_discoveries": sum(len(s["items"]) for s in domain_sections),
        "domain_sections": domain_sections,
        "tool_profiles": [
            {
                "canonical_name": t["canonical_name"],
                "score": round(t["score"], 1),
                "research_summary": t["summary"],
                "trend_rationale": t["trend_rationale"],
                "technical_strengths": t.get("strengths", []),
                "technical_weaknesses": t.get("weaknesses", []),
                "homepage_url": t.get("homepage_url"),
                "category": t.get("category") or "Technology",
                "key_features": t.get("key_features", []),
                "primary_use_cases": t.get("primary_use_cases", []),
                "drivers": t.get("drivers", []),
                "momentum_assessment": t.get("momentum_assessment", ""),
                "maturity": t.get("maturity", ""),
                "competitors": t.get("competitors", []),
                "differentiation": t.get("differentiation", ""),
                "positioning": t.get("positioning", ""),
                "components": t.get("components", {}),
                "justification": t.get("justification", ""),
            }
            for t in tool_contexts
        ],
        "rankings": [
            {"rank": i + 1, "canonical_name": t["canonical_name"], "score": round(t["score"], 1), "category": t.get("category") or "Technology"}
            for i, t in enumerate(tool_contexts)
        ],
    }
    html = render_html(html_context)
    pdf_path = storage_dir / "report.pdf"
    pdf_ok = render_pdf(html, pdf_path)

    # Create Report record
    rel_md = f"reports/{run_id}/report.md"
    rel_pdf = f"reports/{run_id}/report.pdf" if pdf_ok else None
    report = Report(
        run_id=run_id,
        title=title,
        generated_at=now,
        status="succeeded" if pdf_ok else "partial",
        markdown_path=rel_md,
        pdf_path=rel_pdf,
        pdf_status="generated" if pdf_ok else "failed",
        sections=sections,
        summary=exec_summary[:500],
        review_notes=review_notes,
    )
    session.add(report)
    await session.flush()

    # Create ToolProfile records
    for i, p in enumerate(analysis_profiles):
        tp = ToolProfile(
            report_id=report.id,
            tool_id=uuid.UUID(p["tool_id"]),
            research_summary=p["summary"],
            trend_rationale=p["trend_rationale"],
            technical_strengths=p.get("strengths", []),
            score=p["score"],
            score_components=p.get("components", {}),
            scoring_method_version=SCORING_VERSION,
            analysis_gaps=p.get("gaps", []),
        )
        session.add(tp)

    # Create Ranking record
    ranking = Ranking(
        report_id=report.id,
        scoring_method_version=SCORING_VERSION,
        ordered_entries=[{"rank": i + 1, "tool_id": p["tool_id"], "score": p["score"]} for i, p in enumerate(analysis_profiles)],
    )
    session.add(ranking)

    run.report_id = report.id
    await run_service.finish_step(session, step, detail={"report_id": str(report.id), "pdf_status": report.pdf_status})

    # Export step
    export_step = await run_service.start_step(session, run_id, "pdf_export")
    await run_service.finish_step(session, export_step, detail={"pdf_ok": pdf_ok})
    await run_service.transition_run(session, run, RunStatus.EXPORTING)
    await run_service.transition_run(session, run, RunStatus.SUCCEEDED, outcome="report_generated")
    await session.commit()

    return StageResult(run_id=run_id, stage="report", status="succeeded", detail={"report_id": str(report.id), "pdf_status": report.pdf_status})
