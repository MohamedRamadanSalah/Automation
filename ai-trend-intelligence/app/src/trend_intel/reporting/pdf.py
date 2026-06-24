"""WeasyPrint PDF renderer from Markdown → HTML → PDF (T035, FR-014)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt

from trend_intel.core.logging import get_logger

log = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_md_renderer = MarkdownIt()


def _render_markdown(text: str) -> str:
    return _md_renderer.render(text)


def _get_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["markdown"] = _render_markdown
    return env


def _load_css() -> str:
    css_path = _TEMPLATES_DIR / "report.css"
    return css_path.read_text(encoding="utf-8") if css_path.exists() else ""


def render_html(context: dict[str, Any]) -> str:
    """Render the Jinja2 HTML template with the given context."""
    env = _get_jinja_env()
    # Override include_raw to inline CSS
    from jinja2 import pass_context
    css_content = _load_css()

    # Patch template to inline CSS (avoid include_raw extension dependency)
    template_src = (_TEMPLATES_DIR / "report.html.j2").read_text(encoding="utf-8")
    template_src = template_src.replace("{% include_raw 'report.css' %}", css_content)
    tmpl = env.from_string(template_src)
    return tmpl.render(**context)


def render_pdf(html: str, output_path: Path) -> bool:
    """Render HTML to PDF using WeasyPrint. Returns True on success, False on failure (FR-014)."""
    try:
        from weasyprint import HTML, CSS
        output_path.parent.mkdir(parents=True, exist_ok=True)
        HTML(string=html, base_url=str(_TEMPLATES_DIR)).write_pdf(str(output_path))
        log.info("pdf_rendered", path=str(output_path), size_bytes=output_path.stat().st_size)
        return True
    except Exception as exc:
        log.error("pdf_render_failed", error=str(exc), output_path=str(output_path))
        return False
