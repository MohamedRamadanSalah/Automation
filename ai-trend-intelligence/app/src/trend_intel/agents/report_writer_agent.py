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
    max_tokens = 2500
    system_prompt = (
        "You are a senior technology analyst writing a professional industry research report. "
        "Given ranked tool profiles with analysis, write authoritative report sections. "
        "Return ONLY a JSON object with these exact keys:\n"
        "{\n"
        '  "title": "<report title including the date>",\n'
        '  "executive_summary": "<2-3 paragraph professional summary of the trends>",\n'
        '  "trend_analysis": "<2-3 paragraphs about the overall technology landscape>",\n'
        '  "tool_profiles_md": "<markdown with one section per tool: ## Tool Name\\n description, strengths, use cases>",\n'
        '  "recommendations": "<bullet list of actionable recommendations for technology leaders>",\n'
        '  "conclusions": "<1-2 paragraph conclusion>"\n'
        "}\n"
        "Return ONLY the JSON object. No extra text, no markdown fences, no wrapper."
    )
