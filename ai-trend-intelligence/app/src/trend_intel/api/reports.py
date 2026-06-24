"""Reports endpoints."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trend_intel.config import get_settings
from trend_intel.db.session import get_session
from trend_intel.models.reports import Report as ReportModel

router = APIRouter(tags=["reports"])


@router.get("/reports", response_model=list[dict])
async def list_reports(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(select(ReportModel).order_by(ReportModel.generated_at.desc()))
    return [
        {"id": str(r.id), "title": r.title, "status": r.status, "generated_at": r.generated_at.isoformat(), "summary": r.summary}
        for r in result.scalars()
    ]


@router.get("/reports/{report_id}", response_model=dict)
async def get_report(report_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(select(ReportModel).where(ReportModel.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": str(report.id),
        "title": report.title,
        "status": report.status,
        "sections": report.sections,
        "summary": report.summary,
        "review_notes": report.review_notes,
        "markdown_path": report.markdown_path,
        "pdf_path": report.pdf_path,
        "pdf_status": report.pdf_status,
        "generated_at": report.generated_at.isoformat(),
    }


@router.get("/reports/{report_id}/pdf")
async def get_report_pdf(report_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> FileResponse:
    result = await session.execute(select(ReportModel).where(ReportModel.id == report_id))
    report = result.scalar_one_or_none()
    if report is None or report.pdf_path is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    settings = get_settings()
    pdf_file = Path(settings.storage_root) / report.pdf_path
    if not pdf_file.exists():
        raise HTTPException(status_code=404, detail="PDF file missing from storage")
    return FileResponse(str(pdf_file), media_type="application/pdf", filename=f"report-{report_id}.pdf")
