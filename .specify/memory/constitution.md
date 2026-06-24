<!--
SYNC IMPACT REPORT
Version change: (template, unratified) → 1.0.0
Ratification: initial adoption of baseline engineering principles already documented in plan.md.
Modified principles: all 5 placeholders replaced with concrete principles.
Added sections: Core Principles (5), Additional Constraints, Development Workflow, Governance.
Removed sections: none.
Templates requiring updates:
  ✅ plan.md Constitution Check — already aligned (lists these 5 baseline gates).
  ✅ spec-template.md — no change required (no constitution-driven mandatory sections added).
  ✅ tasks-template.md — no change required.
  ✅ .specify/templates/commands/* — no outdated agent-specific references found.
Follow-up TODOs: none. RATIFICATION_DATE set to first adoption date 2026-06-24.
-->

# AI Trend Intelligence Platform Constitution

## Core Principles

### I. Modularity (Pluggable by Design)

Every external integration point MUST be a replaceable unit behind a stable interface.
Discovery sources are adapters loaded from a registry; AI agents are role classes behind a
common base; report sections are template-driven. Adding a source, swapping a model, or adding
a report section MUST require changes only to that unit and its configuration — never to
unrelated layers. Rationale: the platform's value depends on growing sources, models, and
sections over time without re-architecting (FR-022, FR-023, FR-024).

### II. Testability (Independently Verifiable Slices)

Each user story MUST be an independently testable vertical slice. Domain logic (dedup, scoring,
validation) MUST be unit-testable without network or AI calls; endpoints MUST have contract
tests; external services (OpenRouter, source APIs) MUST be mockable. A task is not "done" until
its behavior is verified. Rationale: the operator explicitly requires accuracy and error
detection — untestable code cannot guarantee either (SC-004, SC-012).

### III. Simplicity / YAGNI

Prefer the simplest design that satisfies the requirement. Do not add infrastructure for
hypothetical futures: n8n is the orchestrator/job runner (no separate task-queue framework);
there is no end-user frontend; one shared model is the default. New dependencies and new
services MUST be justified against a concrete present need. Rationale: a single-operator local
system is best served by minimal moving parts.

### IV. Observability (Nothing Fails Silently)

Every run MUST record per-step status with enough detail to diagnose failures without inspecting
raw provider responses. A run that cannot produce a valid report MUST end in an explicit
failure/empty outcome — never a partial result presented as complete. Logging MUST be
structured. Rationale: built-in error detection is a stated requirement (FR-017, SC-010, SC-013).

### V. Security (Secrets Never Leak)

Configured secrets (API keys, credentials) MUST be injected via environment/Docker secrets and
MUST NEVER appear in reports, stored output, or logs — enforced by a single redaction chokepoint
and verified by tests. Fetched external content is untrusted: fetches use timeouts, size caps,
and scheme allowlists; agent output is schema-validated before persistence or rendering. Service
ports bind to localhost in the single-operator deployment. Rationale: FR-027, SC-011, R12.

## Additional Constraints

- **Technology stack** (fixed for v1): Python 3.12+, FastAPI, SQLAlchemy 2.0 async + PostgreSQL 16,
  Alembic, n8n (orchestration), OpenRouter via the OpenAI-compatible SDK, WeasyPrint (PDF), all
  run via Docker Compose. Deviations require an entry in the plan's Complexity Tracking table.
- **Deployment model**: self-hosted, single-operator, local. Multi-tenant auth, public sign-up,
  and external delivery channels are out of scope for v1.
- **Reproducibility**: scoring is a versioned, code-computed weighted composite; per-run config is
  snapshotted so any report can be explained after the fact.

## Development Workflow

- Work follows the Spec-Driven flow: `specify → clarify → plan → tasks → analyze → implement`.
- Tasks are organized by prioritized user story; the P1 story is a shippable MVP and each later
  story is an independent increment that must not break prior ones.
- Within a story: tests precede implementation (verify red before green); models → services →
  endpoints → integration.
- Commit after each task or logical group; validate at each story checkpoint before advancing.

## Governance

This constitution supersedes ad-hoc practices for this project. Amendments MUST be recorded in
this file with a Sync Impact Report and a semantic version bump:

- **MAJOR**: removal or backward-incompatible redefinition of a principle.
- **MINOR**: a new principle or materially expanded guidance.
- **PATCH**: clarifications and wording fixes.

All plans MUST pass the Constitution Check gate in `plan.md`; any violation MUST be justified in
the Complexity Tracking table or the design MUST be simplified. Compliance is reviewed at each
spec-kit phase boundary.

**Version**: 1.0.0 | **Ratified**: 2026-06-24 | **Last Amended**: 2026-06-24
