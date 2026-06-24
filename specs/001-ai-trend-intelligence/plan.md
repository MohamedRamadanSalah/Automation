# Implementation Plan: AI Trend Intelligence Platform

**Branch**: `001-ai-trend-intelligence` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-ai-trend-intelligence/spec.md`

## Summary

A self-hosted, single-operator platform that automatically produces premium technology research reports. **n8n** orchestrates a scheduled/manual pipeline that calls a **Python 3.12 / FastAPI** service through discrete stage endpoints: discover trending tools from multiple pluggable sources → validate (normalized + fuzzy dedup, quality, popularity, source verification) → run seven AI agent roles via a single configurable **OpenRouter** model → assemble a Markdown report → render a premium **PDF** (WeasyPrint, CSS paged media) → persist everything to **PostgreSQL** + a local file volume as queryable historical intelligence. Each run is a tracked background job with per-step status and error detection; the Quality Reviewer drives a bounded auto-revision loop. Modularity (pluggable source adapters, role-based agents, configurable models/thresholds) is the central design principle so sources, models, and report sections can grow without re-architecting.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastAPI (+ Uvicorn), Pydantic v2 & pydantic-settings, SQLAlchemy 2.0 async + asyncpg, Alembic (migrations), httpx (async HTTP), OpenAI SDK pointed at OpenRouter (`base_url=https://openrouter.ai/api/v1`), rapidfuzz (fuzzy dedup), feedparser (RSS), trafilatura (article text extraction), selectolax (HTML parsing), WeasyPrint + Jinja2 + markdown-it-py (Markdown→HTML→PDF), tenacity (bounded retry), structlog (structured logging)

**Storage**: PostgreSQL 16 (relational data, history) + local file volume `storage/reports/{run_id}/` for `report.md` and `report.pdf`

**Testing**: pytest, pytest-asyncio, httpx ASGI test client, respx (mock OpenRouter/HTTP), a disposable PostgreSQL service for integration tests

**Target Platform**: Linux containers via Docker Compose; runs locally on the operator's machine

**Project Type**: Backend web-service (FastAPI) + n8n orchestration + PostgreSQL — no end-user frontend in scope

**Performance Goals**: Run executes as an asynchronous tracked background job, optimized for speed *subject to accuracy*; no fixed wall-clock SLA (per Clarifications 2026-06-24). Per-step status enables early error detection; AI calls run concurrently across tools where independent.

**Constraints**: Single-operator local deployment (no multi-tenant auth in v1); one shared OpenRouter model by default, overridable per agent role; respect each source's ToS / robots policy; configured secrets MUST never appear in reports, stored output, or logs; bounded retries — never hang.

**Scale/Scope**: ~10–20 tools per report (configurable); the 8 named sources (Product Hunt, GitHub Trending, Hacker News, Reddit, Dev.to, Medium, tech blogs, AI news sites) are served by 6 adapter modules across 3 access categories (`api`/`graphql`/`rss`) — the single RSS adapter covers Medium, tech blogs, and AI-news feeds via configurable feed lists; weekly default cadence + on-demand; retain all report history indefinitely (v1 default).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution (`.specify/memory/constitution.md`) is **ratified at v1.0.0** (2026-06-24) with five principles: I. Modularity, II. Testability, III. Simplicity/YAGNI, IV. Observability, V. Security. The plan is gated against each, and satisfies all:

| Gate | Status | How the design satisfies it |
|------|--------|------------------------------|
| **Modularity** | ✅ PASS | Pluggable source adapters via a registry; role-based agents behind a common base; report sections template-driven. Adding a source/model/section requires no change to unrelated layers (FR-022/023/024). |
| **Testability** | ✅ PASS | Stage endpoints and pure domain services are independently testable; contract tests per endpoint; OpenRouter/HTTP mocked via respx. Each user story is an independent vertical slice. |
| **Simplicity / YAGNI** | ✅ PASS | No task-queue framework (Celery/RQ) — n8n is the orchestrator/job runner. No frontend. Single shared model by default. |
| **Observability** | ✅ PASS | Structured logging (structlog) + a `runs`/`run_steps` audit trail with per-step status and failure reasons (FR-017, SC-013). |
| **Security** | ✅ PASS | Secrets via env/Docker secrets, never persisted or logged; secret-redaction in the logging layer (FR-027, SC-011). |

**Result**: No violations. Complexity Tracking table not required. Constitution v1.0.0 principles map 1:1 to the gates above.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-trend-intelligence/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output — technology decisions & rationale
├── data-model.md        # Phase 1 output — entities, schema, state transitions
├── quickstart.md        # Phase 1 output — run & validate end-to-end
├── contracts/           # Phase 1 output
│   ├── openapi.yaml         # FastAPI HTTP contract (stage + query endpoints)
│   ├── agents.md            # Agent role I/O contracts (structured JSON)
│   └── n8n-workflow.md      # Orchestration workflow node-by-node contract
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
ai-trend-intelligence/
├── docker-compose.yml            # api + n8n + postgres (+ volumes, network)
├── .env.example                  # all config keys & secrets (no real values)
├── README.md
├── app/                          # FastAPI service
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/               # Alembic versions
│   ├── src/trend_intel/
│   │   ├── main.py               # app factory, router mounting, lifespan
│   │   ├── config.py             # pydantic-settings (env-driven)
│   │   ├── core/                 # logging, secret redaction, errors, retry, scoring
│   │   ├── db/                   # async engine, session, base
│   │   ├── models/               # SQLAlchemy ORM (see data-model.md)
│   │   ├── schemas/              # Pydantic DTOs (API + agent I/O)
│   │   ├── discovery/            # source adapters + registry
│   │   │   ├── base.py           # SourceAdapter protocol
│   │   │   ├── registry.py       # config-driven adapter loading (FR-023)
│   │   │   └── sources/          # producthunt, github, hackernews, reddit, devto, rss
│   │   ├── collection/           # crawl/scrape/RSS/article-extraction helpers
│   │   ├── validation/           # normalize, fuzzy-dedup, quality, popularity, verify
│   │   ├── agents/               # base agent, openrouter client, 7 role agents
│   │   ├── reporting/            # markdown assembler, jinja templates, weasyprint renderer
│   │   │   └── templates/        # report.html.j2 + report.css (premium paged-media)
│   │   ├── history/              # historical intelligence queries & comparison
│   │   ├── orchestration/        # run service, stage coordinators, status tracking
│   │   └── api/                  # routers: runs, stages, reports, tools, health
│   └── tests/{contract,integration,unit}/
├── n8n/
│   └── workflows/                # exported workflow JSON (schedule + manual webhook)
├── db/
│   └── init/                     # optional bootstrap SQL (Alembic is source of truth)
├── docs/                         # operator/developer docs (e.g., adding-a-source.md)
└── storage/                      # mounted volume: reports/{run_id}/{report.md,report.pdf}
```

**Structure Decision**: A **single backend service** (`app/`) plus **n8n** and **PostgreSQL** as sibling Compose services. The spec's eight architectural layers map 1:1 to packages inside `app/src/trend_intel/` (discovery, collection, validation, agents, reporting, history, orchestration, api), keeping each layer independently testable and replaceable. There is no frontend/backend split because no end-user UI is in scope; n8n provides the operator-facing orchestration surface.

## Architecture Overview

```text
         ┌────────── n8n (Orchestration Layer) ──────────┐
         │  Schedule Trigger ── or ── Manual Webhook      │
         │     │                                          │
         │     ▼  (HTTP calls, error branches, retries)   │
         └─────┼──────────────────────────────────────────┘
               ▼
   ┌─────────────────────── FastAPI service (app/) ───────────────────────┐
   │  api/  →  orchestration/ (run + step status)                          │
   │   discovery → collection → validation → agents → reporting → history  │
   └───────┬───────────────────────────────────┬───────────────┬──────────┘
           ▼                                     ▼               ▼
    External sources                       OpenRouter        PostgreSQL 16
 (PH, GitHub, HN, Reddit,                 (1 shared model,  + file volume
  Dev.to, Medium/RSS, blogs)               per-role override) storage/reports/
```

**Agent communication flow** (per validated tool, fan-out then aggregate):
`Research → Trend Analysis → Technical Analyst → Comparison → Ranking` produce structured JSON attached to the tool; `Report Writer` assembles sections across all tools; `Quality Reviewer` evaluates the draft and drives a **bounded revise→re-review loop** (FR-010) before finalize. Each agent validates its own structured output and retries malformed responses (FR-017a) — see `contracts/agents.md`.

## Complexity Tracking

> No Constitution violations — table intentionally empty.

## Phase Outputs

- **Phase 0** → [research.md](./research.md): all technology choices resolved (PDF engine, async/orchestration model, source adapters, fuzzy matching, agent/structured-output approach, scoring formula). No `NEEDS CLARIFICATION` remain.
- **Phase 1** → [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md): relational schema + state machine, HTTP/agent/workflow contracts, and an end-to-end validation guide.

## Deliverables Coverage Map

The 12 requested deliverables map to these artifacts:

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | System architecture | plan.md → *Architecture Overview*; research.md |
| 2 | Folder structure | plan.md → *Project Structure* |
| 3 | Docker architecture | research.md (R2, R10); quickstart.md |
| 4 | Docker Compose config | quickstart.md (described); built in `/speckit-implement` |
| 5 | Database schema | data-model.md |
| 6 | n8n workflow design | contracts/n8n-workflow.md |
| 7 | FastAPI service structure | plan.md *Project Structure*; contracts/openapi.yaml |
| 8 | Agent communication flow | plan.md *Architecture*; contracts/agents.md |
| 9 | Python implementation plan | plan.md; sequenced concretely by `/speckit-tasks` |
| 10 | Scalability considerations | research.md (R11) |
| 11 | Security considerations | research.md (R12) |
| 12 | Step-by-step roadmap | research.md (R13); enumerated by `/speckit-tasks` |
