---
description: "Task list for AI Trend Intelligence Platform implementation"
---

# Tasks: AI Trend Intelligence Platform

**Input**: Design documents from `specs/001-ai-trend-intelligence/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: INCLUDED — the spec's clarified priority on accuracy and built-in error detection (Clarifications 2026-06-24, FR-017a, SC-012/013) justifies contract tests per endpoint, integration tests per story, and unit tests for critical logic (dedup, scoring, secret redaction).

**Organization**: Tasks are grouped by user story (P1–P5) so each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US5 maps to the spec's prioritized user stories
- All paths are relative to repo root; the service lives under `app/src/trend_intel/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and container scaffolding

- [x] T001 Create the repository structure per plan.md: `app/src/trend_intel/{core,db,models,schemas,discovery,collection,validation,agents,reporting,history,orchestration,api}/`, `app/tests/{contract,integration,unit}/`, `n8n/workflows/`, `db/init/`, `storage/reports/` (with `.gitkeep` files)
- [x] T002 Initialize the Python project in `app/pyproject.toml` (Python 3.12) with dependencies: fastapi, uvicorn[standard], pydantic, pydantic-settings, sqlalchemy[asyncio], asyncpg, alembic, httpx, openai, rapidfuzz, feedparser, trafilatura, selectolax, weasyprint, jinja2, markdown-it-py, tenacity, structlog; dev: pytest, pytest-asyncio, respx
- [x] T003 [P] Create `app/Dockerfile` (`python:3.12-slim`, system deps for WeasyPrint — libpango/cairo/gdk-pixbuf, non-root `appuser`, uvicorn entrypoint)
- [x] T004 [P] Create `docker-compose.yml` with services `api` (build app/, port 127.0.0.1:8000), `n8n` (`n8nio/n8n`, port 127.0.0.1:5678, basic auth + encryption key env), `postgres` (`postgres:16`, named volume); shared `storage/` bind mount into api; private network
- [x] T005 [P] Create `.env.example` with all non-secret keys + placeholder secret keys (OPENROUTER_API_KEY, OPENROUTER_DEFAULT_MODEL, POSTGRES_*, N8N_*, optional source creds, AGENT_CONCURRENCY, AGENT_MAX_RETRIES, REVIEW_MAX_ATTEMPTS, REVIEW_PASS_THRESHOLD, POPULARITY_THRESHOLD, TOP_N)
- [x] T006 [P] Configure ruff + mypy in `app/pyproject.toml`
- [x] T007 [P] Create `.gitignore` (`.env`, `storage/reports/*`, `__pycache__`, `.pytest_cache`, `*.pyc`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T008 Implement `app/src/trend_intel/config.py` — pydantic-settings `Settings` loading all env keys (DB URL, OpenRouter, thresholds, concurrency, review loop params)
- [x] T009 [P] Implement `app/src/trend_intel/core/logging.py` — structlog setup with a **secret-redaction processor** that masks known secret keys/values (FR-027, SC-011)
- [x] T010 [P] Implement `app/src/trend_intel/core/errors.py` — domain exceptions + FastAPI exception handlers returning the `Error` schema
- [x] T011 [P] Implement `app/src/trend_intel/core/retry.py` — tenacity-based bounded retry helper with backoff (FR-025)
- [x] T012 Implement `app/src/trend_intel/db/base.py` (DeclarativeBase) and `db/session.py` (async engine + session factory + `get_session` dependency)
- [x] T013 [P] Create ORM models `discovery_sources.py`, `candidates.py`, `tools.py` in `app/src/trend_intel/models/` per data-model.md
- [x] T014 [P] Create ORM models `runs.py`, `run_steps.py` in `app/src/trend_intel/models/` per data-model.md
- [x] T015 [P] Create ORM models `reports.py`, `tool_profiles.py`, `rankings.py` in `app/src/trend_intel/models/` per data-model.md
- [x] T016 [P] Create ORM models `scoring_methods.py`, `agent_configs.py` in `app/src/trend_intel/models/` per data-model.md
- [x] T017 Initialize Alembic in `app/migrations/` and author the baseline migration creating all 10 tables with indexes + UNIQUE constraints, and seed `scoring_methods` `v1` (weights 0.30/0.30/0.25/0.15) — depends on T013–T016
- [x] T018 [P] Implement shared Pydantic DTOs in `app/src/trend_intel/schemas/` (Error, Health, Run, RunStep, RunDetail, StageResult) per contracts/openapi.yaml
- [x] T019 Implement `app/src/trend_intel/main.py` — FastAPI app factory, lifespan (DB connect), router mounting, and `GET /health` (db up/down) per openapi.yaml
- [x] T020 [P] Implement `app/src/trend_intel/core/security.py` — optional API-key dependency stub (no-op when unset) for mutating endpoints
- [x] T021 Implement `app/src/trend_intel/orchestration/run_service.py` — create run, `runs` state transitions, and `run_steps` start/finish/fail helpers with redacted detail (FR-017, SC-013) — depends on T014, T012
- [x] T022 [P] Implement `app/src/trend_intel/agents/openrouter_client.py` (OpenAI SDK → OpenRouter base_url) and `agents/base.py` `BaseAgent` (JSON mode, Pydantic-validated output, corrective re-prompt + bounded retry) per contracts/agents.md (FR-017a, SC-012) — depends on T011, T008

**Checkpoint**: Foundation ready — schema migrates, app boots, `/health` passes, run/step tracking + agent base exist.

---

## Phase 3: User Story 1 — Automated End-to-End Report Generation (Priority: P1) 🎯 MVP

**Goal**: A single trigger runs discovery (one source) → minimal validation → basic AI analysis → Markdown + premium PDF with all 8 sections → persisted + stored, driven by an n8n workflow.

**Independent Test**: Trigger a run; confirm `status=succeeded`, a stored `report.md` + `report.pdf` with cover, executive summary, TOC, trend analysis, tool profiles, rankings, recommendations, conclusions in order (Scenario A).

### Tests for User Story 1 ⚠️

- [x] T023 [P] [US1] Contract test for `POST /runs` and `GET /runs/{id}` in `app/tests/contract/test_runs.py`
- [x] T024 [P] [US1] Contract test for stage endpoints (discover/validate/analyze/report) in `app/tests/contract/test_stages.py`
- [x] T025 [P] [US1] Integration test: end-to-end run produces a report with all 8 sections + a PDF file (OpenRouter mocked via respx) in `app/tests/integration/test_e2e_report.py`. MUST also assert **both** trigger paths work: a `trigger_type=manual` run and a `trigger_type=scheduled` run each create a run and reach `succeeded` (FR-016).

### Implementation for User Story 1

- [x] T026 [P] [US1] Implement `app/src/trend_intel/discovery/base.py` — `SourceAdapter` protocol + `CandidateDTO`
- [x] T027 [P] [US1] Implement `app/src/trend_intel/discovery/sources/hackernews.py` — HN Firebase API adapter
- [x] T028 [US1] Implement discovery service + `POST /runs/{run_id}/discover` in `app/src/trend_intel/api/stages.py` (persist candidates, record skipped sources) — depends on T026, T027, T021
- [x] T029 [US1] Implement minimal validation (name normalization + exact-normalized dedup + popularity threshold) in `app/src/trend_intel/validation/service.py` + wire `POST /runs/{run_id}/validate` (terminate `no_trends` if empty, FR-026)
- [x] T030 [P] [US1] Implement `app/src/trend_intel/agents/research_agent.py` per contracts/agents.md — depends on T022
- [x] T031 [P] [US1] Implement `app/src/trend_intel/agents/report_writer_agent.py` per contracts/agents.md — depends on T022
- [x] T032 [US1] Implement `app/src/trend_intel/core/scoring.py` with a basic raw-popularity ranking (placeholder for US3 composite) + ranking persistence
- [x] T033 [US1] Implement analyze stage (per-tool Research + ranking) + `POST /runs/{run_id}/analyze` in `app/src/trend_intel/api/stages.py` — depends on T030, T032
- [x] T034 [P] [US1] Create premium templates `app/src/trend_intel/reporting/templates/report.html.j2` + `report.css` (CSS paged media: cover page, generated TOC via target-counter, running headers/footers, per-section page breaks, all 8 sections, FR-013)
- [x] T035 [US1] Implement `reporting/markdown.py` (assemble ordered Markdown) + `reporting/pdf.py` (WeasyPrint render; retain MD on PDF failure, FR-014) — depends on T034, T031
- [x] T036 [US1] Implement report stage: assemble MD + single quality-review pass + PDF + persist `reports`/`tool_profiles`/`rankings` + write files to `storage/reports/{run_id}/` + `POST /runs/{run_id}/report`, `GET /reports/{id}`, `GET /reports/{id}/pdf` — depends on T035, T033
- [x] T037 [US1] Author n8n workflow `n8n/workflows/trend-intelligence-run.json` (schedule + manual webhook → stage calls with error branches) per contracts/n8n-workflow.md + import instructions in README

**Checkpoint**: MVP — one trigger yields a complete premium report end-to-end (SC-001, SC-002, SC-003).

---

## Phase 4: User Story 2 — Multi-Source Discovery & Validation (Priority: P2)

**Goal**: Discover across all configured sources, dedup via normalized+fuzzy matching, apply quality/popularity/source-verification with recorded exclusions, and stay resilient to a failing source.

**Independent Test**: Run discovery across ≥2 overlapping sources; validated list has zero duplicates, each entry traces to a verifiable source, excluded items carry reasons, and a disabled/broken source is listed in `skipped_sources` without aborting (Scenarios C, D).

### Tests for User Story 2 ⚠️

- [x] T038 [P] [US2] Unit test for normalized+fuzzy dedup (`Tool.ai`/`Tool AI`/`tool-ai` collapse) in `app/tests/unit/test_dedup.py`
- [x] T039 [P] [US2] Integration test: multi-source discovery + dedup + resilience to a failing source in `app/tests/integration/test_discovery_validation.py`

### Implementation for User Story 2

- [x] T040 [P] [US2] Implement `app/src/trend_intel/discovery/registry.py` — config-driven adapter loading from `discovery_sources` (FR-023)
- [x] T041 [P] [US2] Implement `app/src/trend_intel/discovery/sources/github.py` — GitHub Search API trending adapter
- [x] T042 [P] [US2] Implement `app/src/trend_intel/discovery/sources/reddit.py` — Reddit OAuth API adapter
- [x] T043 [P] [US2] Implement `app/src/trend_intel/discovery/sources/devto.py` — Dev.to Forem API adapter
- [x] T044 [P] [US2] Implement `app/src/trend_intel/discovery/sources/producthunt.py` — Product Hunt GraphQL adapter
- [x] T045 [P] [US2] Implement `app/src/trend_intel/discovery/sources/rss.py` — feedparser adapter for Medium/tech-blogs/AI-news feeds
- [x] T046 [US2] Implement `app/src/trend_intel/collection/fetch.py` — httpx fetch + trafilatura article extraction + selectolax parsing + robots.txt check + per-source rate limiting (R5, R12)
- [x] T047 [US2] Upgrade `validation/service.py` to full pipeline: rapidfuzz normalized+fuzzy dedup + URL/domain match (FR-004), quality checks, source verification, popularity threshold (FR-006), and exclusion-reason recording (FR-005) — depends on T046
- [x] T048 [US2] Make discovery resilient: per-source timeout + `asyncio.gather(return_exceptions=True)` + populate `runs.skipped_sources` (FR-002) — depends on T040, T028

**Checkpoint**: Trustworthy, deduplicated, multi-source validated input (SC-005, SC-006, SC-007).

---

## Phase 5: User Story 3 — Multi-Agent Deep Analysis & Ranking (Priority: P3)

**Goal**: Full seven-role analysis per tool with structured/validated output, four-dimension versioned scoring computed in code, bounded Quality-Reviewer revise→re-review loop, and per-tool failure isolation.

**Independent Test**: Feed a validated tool through analysis; confirm research/trend/technical/comparison/score all produced; a forced single-tool agent failure is isolated as an `analysis_gap` without aborting; reviewer loop runs within attempt cap (Scenario B + analysis checks).

### Tests for User Story 3 ⚠️

- [x] T049 [P] [US3] Unit test for the 4-dimension weighted composite scoring + version tag in `app/tests/unit/test_scoring.py`
- [x] T050 [P] [US3] Integration test: full agent fan-out + bounded review loop + per-tool failure isolation (OpenRouter mocked) in `app/tests/integration/test_analysis.py`

### Implementation for User Story 3

- [x] T051 [P] [US3] Implement `app/src/trend_intel/agents/trend_agent.py` per contracts/agents.md
- [x] T052 [P] [US3] Implement `app/src/trend_intel/agents/technical_agent.py` per contracts/agents.md
- [x] T053 [P] [US3] Implement `app/src/trend_intel/agents/comparison_agent.py` per contracts/agents.md
- [x] T054 [P] [US3] Implement `app/src/trend_intel/agents/ranking_agent.py` (per-dimension 0–100 values) per contracts/agents.md
- [x] T055 [P] [US3] Implement `app/src/trend_intel/agents/quality_reviewer_agent.py` per contracts/agents.md
- [x] T056 [US3] Replace placeholder scoring in `core/scoring.py` with the versioned weighted composite over the four dimensions, persisting `score_components` + `scoring_method_version` (FR-008, R8) — depends on T054
- [x] T057 [US3] Upgrade analyze stage to full per-tool fan-out (Research→Trend→Technical→Comparison→Ranking) under `asyncio.Semaphore(AGENT_CONCURRENCY)` with per-tool failure isolation → `analysis_gaps` (FR-011) — depends on T051–T054, T056
- [x] T058 [US3] Upgrade report stage with the bounded Quality-Reviewer revise→re-review loop (up to `REVIEW_MAX_ATTEMPTS`) persisting unresolved notes to `reports.review_notes` (FR-010) — depends on T055, T036

**Checkpoint**: Premium analytical depth + reproducible ranking + self-correcting quality (SC-004, SC-010, SC-012).

---

## Phase 6: User Story 4 — Historical Intelligence & Trend Evolution (Priority: P4)

**Goal**: Query a tool's appearance history and compare two reports (new/dropped/rank changes).

**Independent Test**: With two reports stored, `/reports/compare` returns new/dropped/rank-changed tools and `/tools/{id}/history` lists each appearance + score within seconds (Scenario E).

### Tests for User Story 4 ⚠️

- [ ] T059 [P] [US4] Contract test for `GET /reports/compare` and `GET /tools/{id}/history` in `app/tests/contract/test_history.py`
- [ ] T060 [P] [US4] Integration test: two-report comparison (new/dropped/rank-change) in `app/tests/integration/test_history.py`. MUST also assert that **two runs triggered on the same day produce two distinct, separately stored reports** (no overwrite) and that tool history lists both appearances (FR-021).

### Implementation for User Story 4

- [ ] T061 [US4] Implement tool history query + `GET /tools/{tool_id}/history` in `app/src/trend_intel/history/service.py` + `api/history.py` (FR-019)
- [ ] T062 [US4] Implement report comparison (new/dropped/rank-delta) + `GET /reports/compare` (FR-020, SC-008) — depends on T061
- [ ] T063 [US4] Maintain `tools.first_seen_at`/`last_seen_at` on tool upsert during validation (FR-019)

**Checkpoint**: Reports become a comparable intelligence asset (SC-008).

---

## Phase 7: User Story 5 — Configurable Models & Future Expansion (Priority: P5)

**Goal**: Change a role's model, add a source, and adjust thresholds/cadence — all via configuration, no code change to unrelated parts.

**Independent Test**: Change Ranking's model via `PUT /config/agents`; add an RSS source via `POST /config/sources`; both take effect next run with no other changes (Scenario F).

### Tests for User Story 5 ⚠️

- [ ] T064 [P] [US5] Contract test for `GET/PUT /config/agents` and `GET/POST /config/sources` in `app/tests/contract/test_config.py`

### Implementation for User Story 5

- [ ] T065 [P] [US5] Implement agent-config endpoints `GET/PUT /config/agents` + per-role model resolution in `agents/base.py` (override → shared default fallback, FR-022) in `app/src/trend_intel/api/config.py` — depends on T022
- [ ] T066 [P] [US5] Implement source-config endpoints `GET/POST /config/sources` wired to the registry (FR-023) in `app/src/trend_intel/api/config.py` — depends on T040
- [ ] T067 [US5] Support per-run overrides (top_n, popularity_threshold) in `RunCreate` and persist `runs.config_snapshot` (FR-024)
- [ ] T068 [US5] Make schedule cadence configurable in the n8n workflow + document in README (default weekly)
- [ ] T069 [P] [US5] Write "Add a new discovery source" developer guide in `docs/adding-a-source.md`

**Checkpoint**: Platform is configurable and extensible without re-architecting (SC-009).

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T070 [P] Secret-redaction unit tests (logs/output never contain secrets) in `app/tests/unit/test_redaction.py` (SC-011)
- [ ] T071 [P] Error-path & retry integration tests (provider failure, malformed agent output, PDF failure) in `app/tests/integration/test_error_paths.py` (SC-007, SC-010, SC-012, SC-013)
- [ ] T072 Premium template polish pass (typography scale, cover art, header/footer running titles, page numbers) in `reporting/templates/`
- [ ] T073 [P] Write `README.md` (setup, env, compose up, workflow import) + link design docs
- [ ] T074 Security hardening: localhost-only port binding, non-root container, URL scheme allowlist + fetch size caps, n8n basic auth (R12)
- [ ] T075 [P] Verify DB indexes from data-model.md exist; tune `AGENT_CONCURRENCY` defaults (R11)
- [ ] T076 Ensure structured logging + `run_steps` detail coverage across all stages (SC-013)
- [ ] T077 Execute all quickstart.md scenarios A–H and record outcomes
- [ ] T078 [P] Additional unit tests for source adapters (parsing fixtures) in `app/tests/unit/test_adapters.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Stories (Phase 3–7)**: All depend on Foundational. Recommended order P1→P2→P3→P4→P5 (priority). US2–US5 build on US1's pipeline but each remains independently testable.
- **Polish (Phase 8)**: Depends on the targeted user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational. Self-contained MVP (one source, basic agents).
- **US2 (P2)**: After Foundational. Extends discovery/validation; upgrades T029's validation (T047) and T028's discovery (T048).
- **US3 (P3)**: After Foundational. Extends agents/scoring; upgrades T032 (→T056), T033 (→T057), T036 (→T058).
- **US4 (P4)**: After US1 (needs ≥1 report); fully independent thereafter.
- **US5 (P5)**: After Foundational; touches agent base (T065) and registry (T066) — best after US2/US3 exist.

### Within Each User Story

- Tests written first and expected to fail before implementation
- Models → services → endpoints → integration
- Story complete and checkpoint-validated before next priority

### Parallel Opportunities

- Setup: T003–T007 in parallel
- Foundational: T009–T011, T013–T016, T018, T020, T022 in parallel (after T008/T012 as noted)
- US1 tests T023–T025 in parallel; agents T030/T031 and template T034 in parallel
- US2 adapters T041–T045 in parallel; tests T038/T039 in parallel
- US3 agents T051–T055 in parallel; tests T049/T050 in parallel
- Different stories can be staffed in parallel once Foundational completes

---

## Parallel Example: User Story 2 (source adapters)

```bash
# After the registry (T040), build all adapters together:
Task: "Implement github adapter in app/src/trend_intel/discovery/sources/github.py"
Task: "Implement reddit adapter in app/src/trend_intel/discovery/sources/reddit.py"
Task: "Implement devto adapter in app/src/trend_intel/discovery/sources/devto.py"
Task: "Implement producthunt adapter in app/src/trend_intel/discovery/sources/producthunt.py"
Task: "Implement rss adapter in app/src/trend_intel/discovery/sources/rss.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup → 2. Phase 2 Foundational (CRITICAL) → 3. Phase 3 US1 → 4. **STOP & VALIDATE** Scenario A → 5. Demo: a real premium PDF from one trigger.

### Incremental Delivery

Foundation → US1 (MVP, premium report) → US2 (trustworthy multi-source) → US3 (analytical depth) → US4 (history) → US5 (configurability) → Polish. Each story is a deployable increment that doesn't break prior ones.

---

## Notes

- [P] = different files, no incomplete dependencies
- US2/US3 deliberately **upgrade** specific US1 tasks (validation, analyze, report) rather than duplicate them — noted inline so the MVP stays thin but real
- Tests precede implementation within each story; verify red before green
- Secrets never enter code, logs, or stored output — enforced by T009 and verified by T070
- Commit after each task or logical group; stop at any checkpoint to validate independently

## Total: 78 tasks

| Phase | Tasks | Count |
|-------|-------|-------|
| 1 — Setup | T001–T007 | 7 |
| 2 — Foundational | T008–T022 | 15 |
| 3 — US1 (P1, MVP) | T023–T037 | 15 |
| 4 — US2 (P2) | T038–T048 | 11 |
| 5 — US3 (P3) | T049–T058 | 10 |
| 6 — US4 (P4) | T059–T063 | 5 |
| 7 — US5 (P5) | T064–T069 | 6 |
| 8 — Polish | T070–T078 | 9 |
