"""Report Writer Agent — produces Markdown report sections (FR-012, FR-013)."""
from __future__ import annotations

from pydantic import BaseModel

from trend_intel.agents.base import BaseAgent


class ReportWriterOutput(BaseModel):
    title: str
    executive_summary: str
    trend_analysis: str
    tool_profiles_md: str
    recommendations: str
    conclusions: str


class ReportWriterAgent(BaseAgent[ReportWriterOutput]):
    role = "report_writer"
    output_schema = ReportWriterOutput
    system_prompt = (
        "You are a senior technology analyst writing a premium industry research report. "
        "Given an ordered list of tool profiles with scores and analysis, produce Markdown sections: "
        "title, executive_summary, trend_analysis (overall landscape), tool_profiles_md (one detailed block per tool in rank order), "
        "recommendations (actionable advice), conclusions. "
        "Write in a professional, authoritative tone suitable for a paid industry report. "
        "Return: {\"ok\": true, \"data\": {\"title\": \"...\", \"executive_summary\": \"...\", "
        "\"trend_analysis\": \"...\", \"tool_profiles_md\": \"...\", \"recommendations\": \"...\", \"conclusions\": \"...\"}}"
    )
