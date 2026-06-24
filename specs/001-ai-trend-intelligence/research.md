# Phase 0 Research: AI Trend Intelligence Platform

All decisions below resolve the Technical Context. No `NEEDS CLARIFICATION` markers remain. The user-specified stack (Docker, n8n, Python 3.12+, FastAPI, OpenRouter, PostgreSQL) is treated as fixed; research focuses on the open *how* choices within it.

---

## R1. Orchestration & async execution model

- **Decision**: **n8n is the orchestrator and job runner.** A scheduled trigger (default weekly) and a manual webhook trigger both drive one workflow that calls FastAPI **stage endpoints** in sequence, using n8n's native error branches and retry settings. FastAPI records a `runs` row + `run_steps` rows for status; n8n's own execution log is the secondary trace. No Celery/RQ/Arq.
- **Rationale**: The spec mandates n8n as the orchestration layer and "run as a tracked background job" (FR-015). Letting n8n own sequencing, retries, and error routing removes an entire task-queue dependency (YAGNI) and gives the operator a visual run history for free. FastAPI stays a stateless-per-request service that is easy to test.
- **Alternatives considered**:
  - *FastAPI BackgroundTasks running the whole pipeline in-process* — works for manual dev runs (kept as a secondary `/runs:execute-local` path) but hides progress and duplicates n8n's job role.
  - *Celery/RQ + Redis* — robust but adds a broker + workers the single-operator scope doesn't justify.

## R2. Service topology (Docker)

- **Decision**: Three Compose services on one private network: `api` (FastAPI/Uvicorn), `n8n` (official `n8nio/n8n` image), `postgres` (`postgres:16`). One shared volume `storage/` mounted into `api` for report files; named volumes for `postgres` data and `n8n` data. `api` exposed on `:8000` (localhost), `n8n` on `:5678` (localhost).
- **Rationale**: Minimal production-shaped topology; n8n reaches `api` by service DNS (`http://api:8000`). Localhost-only port binding fits single-operator security posture.
- **Alternatives**: Separate Postgres instances for n8n vs app (rejected — one instance with separate databases/schemas is simpler); running n8n's tasks as raw Python (rejected — loses the orchestration UI the spec wants).

## R3. PDF generation engine

- **Decision**: **WeasyPrint** rendering Jinja2-templated HTML + a dedicated print CSS using **CSS Paged Media** (`@page`, named pages, running headers/footers, `target-counter` for a real Table of Contents, page breaks per section).
- **Rationale**: Pure-Python, no headless browser, excellent paged-media support — ideal for a "looks like a paid industry report" deliverable with cover page, generated TOC, page numbers, and consistent section styling. Renders the same Markdown that is stored as the report source (Markdown → HTML via markdown-it-py, wrapped in the report template).
- **Alternatives considered**:
  - *Playwright/Chromium `print-to-pdf`* — pixel-perfect for complex CSS/JS charts, but adds a ~400MB browser to the image; keep as the documented escape hatch if future charts demand it.
  - *ReportLab* — maximal control but verbose, low-level; poor fit for document-style layout.
  - *wkhtmltopdf* — effectively unmaintained; avoid.

## R4. Discovery source adapters

- **Decision**: A `SourceAdapter` protocol (`async discover() -> list[CandidateDTO]`) with a **config-driven registry** (`discovery/registry.py`). One adapter per source type; enabling/adding a source = a config entry + adapter class (satisfies FR-023). Access strategy per source:

  | Source | Access method | Notes |
  |--------|---------------|-------|
  | Hacker News | Official Firebase API | Free, no auth |
  | Dev.to | Official Forem API | Free, optional key |
  | Reddit | Official API (OAuth app) | Operator supplies client id/secret |
  | Product Hunt | GraphQL API | Operator supplies token |
  | GitHub Trending | GitHub Search API (`stars`, `created:>…`) | Official API instead of scraping the trending HTML page |
  | Medium / Tech blogs / AI news | RSS via `feedparser` | Pluggable list of feed URLs in config |

- **Rationale**: Prefer official APIs (stable, ToS-friendly) over scraping wherever one exists; fall back to RSS for sources without APIs (Medium, blogs). The registry keeps validation/analysis blind to where a candidate came from.
- **Alternatives**: Scraping GitHub's `/trending` HTML (rejected — brittle, ToS-grey; Search API approximates trending via recent-stars queries). A single generic scraper for all (rejected — loses per-source signal fidelity).

## R5. Data collection & article extraction

- **Decision**: `httpx` (async) for fetching; **trafilatura** for main-article text extraction; **selectolax** for targeted HTML parsing; `feedparser` for RSS. Per-source rate limiting (config) and `robots.txt` checks via `urllib.robotparser`.
- **Rationale**: trafilatura is best-in-class for extracting clean article body text (feeds the Research Agent) without boilerplate; selectolax is a fast lxml-free parser for structured bits.
- **Alternatives**: BeautifulSoup (slower), newspaper3k (stale deps), Scrapy (heavy framework — overkill for batch pulls).

## R6. Deduplication / identity resolution

- **Decision**: **Normalized + fuzzy match** (per Clarification): (1) normalize name — lowercase, strip punctuation/whitespace, drop common suffixes (`.ai`, `.io`, `-app`, `app`); (2) **rapidfuzz** `token_sort_ratio` above a configurable threshold (default 90); (3) canonical URL/domain equality as a strong override. Matches merge into one `tool` preserving all source links.
- **Rationale**: Catches `Tool.ai` / `Tool AI` / `tool-ai` near-duplicates that exact matching misses (SC-005 = zero duplicates), without per-candidate AI cost.
- **Alternatives**: Exact match (rejected — fails SC-005 in practice); AI canonical resolution (rejected for default — cost/latency on every candidate; could be a future high-accuracy mode).

## R7. AI agents & structured output

- **Decision**: **OpenAI Python SDK** pointed at OpenRouter (`base_url=https://openrouter.ai/api/v1`, `OPENROUTER_API_KEY`). A `BaseAgent` defines: system prompt, a **Pydantic output model**, JSON-mode request, output **validation + bounded retry** (tenacity) on schema/format failure (FR-017a, SC-012). Seven role subclasses (Research, Trend Analysis, Technical Analyst, Comparison, Ranking, Report Writer, Quality Reviewer). One shared model id from config by default; per-role override map (FR-022). Independent per-tool agent calls run concurrently with a bounded `asyncio.Semaphore`.
- **Rationale**: OpenRouter is OpenAI-compatible, so the mature SDK works unchanged and model swapping is a config string. Pydantic validation turns "accuracy + error detection" into enforced structure rather than hope. Concurrency addresses the "faster" requirement without violating accuracy.
- **Alternatives**: `instructor` library (nice, but the manual pydantic+retry path keeps deps minimal — instructor can be adopted later); LangChain (heavy abstraction not needed for fixed role prompts); raw httpx (loses SDK retry/streaming niceties).

## R8. Ranking score formula

- **Decision**: A **versioned weighted composite** (stored as `scoring_method_version`) over four normalized 0–100 dimensions (per Clarification): `popularity`, `momentum` (growth rate), `technical_merit` (agent-assessed), `source_credibility` (count × reputation of independent sources). Default weights `0.30 / 0.30 / 0.25 / 0.15`, configurable. Each dimension's raw + normalized value is persisted in `tool_profiles.score_components` for reproducibility (FR-008).
- **Rationale**: Explicit, reproducible, and auditable; weights live in config so the formula can evolve without code changes. Persisting components makes any score explainable and lets historical comparison stay valid across weight changes (version tag).
- **Alternatives**: Pure LLM "give it a score" (rejected — not reproducible); fixed hard-coded weights (rejected — not configurable per FR-024).

## R9. Persistence & migrations

- **Decision**: **SQLAlchemy 2.0 (async, asyncpg)** ORM + **Alembic** migrations. Report files (`report.md`, `report.pdf`) live on the `storage/` volume; the DB stores their relative paths plus all structured data and history.
- **Rationale**: Async ORM matches FastAPI's async stack; Alembic gives versioned schema evolution. Files-on-volume + paths-in-DB keeps large binaries out of Postgres while staying queryable.
- **Alternatives**: Storing PDFs as `bytea` in Postgres (rejected — bloats DB, complicates backups); raw SQL without ORM (rejected — loses model/test ergonomics).

## R10. Configuration & secrets

- **Decision**: `pydantic-settings` loading from environment / `.env`; all secrets (OpenRouter key, Reddit/Product Hunt creds, n8n encryption key, DB password) injected as env vars (Docker secrets-compatible). A logging processor **redacts known secret keys** before emit.
- **Rationale**: Twelve-factor config; satisfies FR-027 / SC-011 (secrets never in logs/output) with a single redaction chokepoint.
- **Alternatives**: Config files committed with values (rejected — leak risk); a secrets manager like Vault (rejected — over-engineered for local single-operator).

## R11. Scalability considerations

- Stage endpoints are **stateless** → the `api` service scales horizontally behind a load balancer if ever needed; Postgres is the single source of truth.
- **Per-tool AI fan-out** is concurrency-bounded (`asyncio.Semaphore`) and naturally shardable — a future version can move per-tool analysis to a queue/worker pool without changing contracts.
- **Source adapters** are independent and parallelizable; one slow/failed source can't block others (FR-002) via per-source timeouts + `asyncio.gather(return_exceptions=True)`.
- **Report volume** grows linearly; history queries are indexed (see data-model.md indexes). Partitioning `tool_profiles` by report date is a future option if history grows large.
- **Model throughput/cost** scales by swapping the shared model id or assigning cheaper models to high-volume roles (Research) and stronger models to Ranking/Reviewer.

## R12. Security considerations

- **Secrets**: env/Docker secrets only; redaction in logs; `.env` git-ignored; `.env.example` ships placeholders (FR-027).
- **Network**: all service ports bound to `127.0.0.1`; inter-service traffic on a private Docker network; n8n protected by basic auth + its encryption key.
- **Input/SSRF**: source URLs and fetched content are untrusted — fetches use timeouts, size caps, allowlisted schemes (`http/https`), and `robots.txt` respect; no fetched HTML is executed.
- **Injection**: SQLAlchemy parameterized queries only; agent outputs validated against Pydantic schemas before persistence/rendering; report HTML is escaped/sanitized before WeasyPrint.
- **AuthN/Z**: v1 is single-operator local — the query/admin API is bound to localhost; an API-key dependency stub is included so auth can be switched on if the service is ever exposed.
- **Supply chain**: pinned dependencies (`pyproject.toml` + lock), minimal base image (`python:3.12-slim`), non-root container user.

## R13. Development roadmap (high level)

Ordered to deliver the P1 MVP first, then layer P2–P5 (each an independently testable slice). `/speckit-tasks` will expand each into concrete tasks.

1. **Foundation** — repo skeleton, `pyproject`, Docker Compose (api+n8n+postgres), config, logging+redaction, DB engine/session, Alembic baseline, health endpoint.
2. **P1 MVP (end-to-end thin slice)** — one discovery source (Hacker News), minimal validation, a reduced agent set behind the OpenRouter client, Markdown assembly, WeasyPrint PDF with all 8 sections, persistence + file storage, a `runs` record, and a single n8n workflow that drives it. *Delivers SC-001/002/003.*
3. **P2 Discovery & Validation** — remaining source adapters + registry; normalized+fuzzy dedup; quality/popularity/source-verification with recorded exclusions. *Delivers SC-005/006/007.*
4. **P3 Multi-agent depth & ranking** — all seven roles with structured output + validation/retry; four-dimension scoring; bounded Quality-Reviewer revision loop. *Delivers SC-004/010/012.*
5. **P4 Historical intelligence** — tool appearance history, report-to-report comparison (new/dropped/rank-change) query API. *Delivers SC-008.*
6. **P5 Configurability & expansion** — per-role model overrides, threshold/cadence/top-N config, documented "add a source" path. *Delivers SC-009.*
7. **Hardening** — error-path tests, secret-redaction tests, retries/timeouts, premium-template polish, docs.

---

### Resolved unknowns summary

| Unknown | Resolution |
|---------|------------|
| Sync vs async run | Async, n8n-orchestrated tracked job (R1) |
| PDF engine | WeasyPrint + CSS paged media (R3) |
| GitHub trending access | GitHub Search API, not HTML scraping (R4) |
| Dedup method | rapidfuzz normalized + fuzzy + URL match (R6) |
| Structured agent output | OpenAI SDK→OpenRouter + Pydantic validate/retry (R7) |
| Scoring | Versioned weighted 4-dimension composite (R8) |
| Task queue needed? | No — n8n is the runner (R1) |
