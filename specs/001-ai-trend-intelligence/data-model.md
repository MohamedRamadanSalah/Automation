# Phase 1 Data Model: AI Trend Intelligence Platform

Relational schema for PostgreSQL 16, managed by SQLAlchemy 2.0 + Alembic. Derived directly from the spec's Key Entities and Functional Requirements. All timestamps are `timestamptz` (UTC). Primary keys are `uuid` (server default `gen_random_uuid()`), except small lookup configs which use natural keys.

---

## Entity-Relationship Overview

```text
discovery_sources ──< candidates >── (merge) ── tools ──< tool_profiles >── reports
                                                  │                          │
                                                  └──< (history via profiles) │
runs ──1:0..1── reports                                                       │
runs ──< run_steps                                          rankings ──1:1────┘
agent_configs (role → model)        scoring_methods (version → weights)
```

Legend: `──<` = one-to-many, `>──` = many-to-one, `1:1` / `1:0..1` as labeled.

---

## Tables

### `discovery_sources`
A configured origin of candidates (FR-001, FR-023).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | uuid | PK | |
| `key` | text | UNIQUE, NOT NULL | stable id, e.g. `hackernews` |
| `type` | text | NOT NULL | `api` \| `rss` \| `graphql` |
| `display_name` | text | NOT NULL | |
| `enabled` | bool | NOT NULL default true | |
| `config` | jsonb | NOT NULL default '{}' | feed URLs, query params, rate limits (no secrets) |
| `created_at` / `updated_at` | timestamptz | NOT NULL | |

### `candidates`
A raw discovered item before validation (FR-001, FR-003). Retained for audit/debug.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | uuid | PK | |
| `run_id` | uuid | FK→runs, NOT NULL | which run discovered it |
| `source_id` | uuid | FK→discovery_sources, NOT NULL | |
| `raw_name` | text | NOT NULL | as seen at source |
| `normalized_name` | text | NOT NULL | dedup key input (R6) |
| `url` | text | | originating item URL |
| `canonical_domain` | text | | for URL-match dedup |
| `raw_signals` | jsonb | NOT NULL default '{}' | stars/upvotes/points/etc. |
| `discovered_at` | timestamptz | NOT NULL | |
| `tool_id` | uuid | FK→tools, NULL | set when merged into a tool |
| `validation_status` | text | NOT NULL default 'pending' | `pending`\|`merged`\|`excluded` |
| `exclusion_reason` | text | NULL | required when excluded (FR-005) |

Index: `(run_id)`, `(normalized_name)`, `(tool_id)`.

### `tools`
A validated, deduplicated technology tracked over time (FR-004, FR-019).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | uuid | PK | |
| `canonical_name` | text | NOT NULL | |
| `slug` | text | UNIQUE, NOT NULL | normalized identity key |
| `category` | text | NULL | |
| `homepage_url` | text | NULL | |
| `first_seen_at` | timestamptz | NOT NULL | first report appearance (FR-019) |
| `last_seen_at` | timestamptz | NOT NULL | most recent appearance |
| `source_refs` | jsonb | NOT NULL default '[]' | merged contributing source links (FR-004) |
| `created_at` / `updated_at` | timestamptz | NOT NULL | |

Index: unique `(slug)`; `(canonical_name)`.

### `runs`
A single pipeline execution (FR-015, FR-016, FR-017, FR-021).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | uuid | PK | |
| `trigger_type` | text | NOT NULL | `scheduled`\|`manual` |
| `status` | text | NOT NULL default 'pending' | see state machine below |
| `started_at` | timestamptz | NULL | |
| `finished_at` | timestamptz | NULL | |
| `skipped_sources` | jsonb | NOT NULL default '[]' | which sources were unavailable (FR-002) |
| `failure_reason` | text | NULL | set on `failed` |
| `outcome` | text | NULL | `report_generated`\|`no_trends`\|`failed` (FR-026) |
| `report_id` | uuid | FK→reports, NULL | at most one report (FR-015) |
| `config_snapshot` | jsonb | NOT NULL default '{}' | thresholds/top-N/model map used (reproducibility) |
| `created_at` | timestamptz | NOT NULL | |

Index: `(status)`, `(created_at desc)`.

### `run_steps`
Per-step status for observability & early error detection (FR-017, SC-013).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | uuid | PK | |
| `run_id` | uuid | FK→runs, NOT NULL | |
| `step` | text | NOT NULL | `discovery`\|`validation`\|`research`\|`trend`\|`technical`\|`comparison`\|`ranking`\|`report_write`\|`quality_review`\|`pdf_export`\|`persist` |
| `status` | text | NOT NULL | `pending`\|`running`\|`succeeded`\|`failed`\|`skipped` |
| `attempts` | int | NOT NULL default 0 | retry count (FR-025) |
| `detail` | jsonb | NOT NULL default '{}' | counts, timings, error message (redacted) |
| `started_at` / `finished_at` | timestamptz | NULL | |

Index: `(run_id, step)`.

### `reports`
A finalized intelligence deliverable (FR-012, FR-013, FR-014, FR-018).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | uuid | PK | |
| `run_id` | uuid | FK→runs, UNIQUE NOT NULL | |
| `title` | text | NOT NULL | |
| `generated_at` | timestamptz | NOT NULL | |
| `status` | text | NOT NULL | `succeeded`\|`partial`\|`failed` |
| `markdown_path` | text | NOT NULL | relative path under storage/ (FR-012/014) |
| `pdf_path` | text | NULL | null if PDF failed but MD kept (FR-014) |
| `pdf_status` | text | NOT NULL default 'pending' | `generated`\|`failed`\|`pending` |
| `sections` | jsonb | NOT NULL | ordered list of included sections (FR-013) |
| `summary` | text | NULL | executive summary cache for quick listing |
| `review_notes` | jsonb | NOT NULL default '[]' | unresolved Quality-Reviewer notes (FR-010) |
| `created_at` | timestamptz | NOT NULL | |

Index: `(generated_at desc)`.

### `tool_profiles`
Per-report analytical record for a tool (FR-007, FR-008, FR-019).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | uuid | PK | |
| `report_id` | uuid | FK→reports, NOT NULL | |
| `tool_id` | uuid | FK→tools, NOT NULL | |
| `research_summary` | text | NOT NULL | Research Agent |
| `trend_rationale` | text | NOT NULL | Trend Analysis Agent |
| `technical_strengths` | jsonb | NOT NULL default '[]' | Technical Analyst |
| `technical_weaknesses` | jsonb | NOT NULL default '[]' | Technical Analyst |
| `comparison` | jsonb | NOT NULL default '{}' | competitors + positioning (Comparison Agent) |
| `score` | numeric(5,2) | NOT NULL | composite 0–100 (FR-008) |
| `score_components` | jsonb | NOT NULL | per-dimension raw+normalized (FR-008, R8) |
| `scoring_method_version` | text | FK→scoring_methods, NOT NULL | reproducibility |
| `analysis_gaps` | jsonb | NOT NULL default '[]' | marked missing perspectives (edge case: partial agent success) |
| `created_at` | timestamptz | NOT NULL | |

Constraints: UNIQUE `(report_id, tool_id)` — a tool appears once per report (SC-005). Index: `(tool_id)` for history (FR-019), `(report_id)`.

### `rankings`
The ordered scoring within a report (FR-009).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | uuid | PK | |
| `report_id` | uuid | FK→reports, UNIQUE NOT NULL | one ranking per report |
| `scoring_method_version` | text | FK→scoring_methods, NOT NULL | |
| `ordered_entries` | jsonb | NOT NULL | `[{rank, tool_id, score}]` ordered desc |
| `created_at` | timestamptz | NOT NULL | |

### `scoring_methods`
Versioned scoring definitions (FR-008, R8).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `version` | text | PK | e.g. `v1` |
| `weights` | jsonb | NOT NULL | `{popularity, momentum, technical_merit, source_credibility}` |
| `description` | text | NULL | |
| `created_at` | timestamptz | NOT NULL | |

### `agent_configs`
Model assignment per agent role (FR-022, FR-017a).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `role` | text | PK | one of the 7 roles |
| `model` | text | NULL | null ⇒ use shared default model |
| `params` | jsonb | NOT NULL default '{}' | temperature, max_tokens, etc. |
| `updated_at` | timestamptz | NOT NULL | |

> Note: only the *shared default model id* and secret API key live in env/config, never in this table (FR-027). This table holds non-secret per-role overrides.

---

## State machine — `runs.status`

```text
pending ──► discovering ──► validating ──► analyzing ──► reporting ──► exporting ──► succeeded
   │            │               │              │             │             │
   └────────────┴───────────────┴──────────────┴─────────────┴─────────────┴──► failed
                                │
                                └──(no qualifying tools)──► no_trends   (terminal, FR-026)
```

- `partial`: terminal sub-state of `succeeded` where `reports.status='partial'` (some tools carried `analysis_gaps`, or PDF failed while Markdown succeeded — FR-014).
- Every transition writes/updates the matching `run_steps` row. A `failed` transition always sets `runs.failure_reason` and the failing `run_steps.detail` (redacted).

## Validation rules (from requirements)

- **Dedup (FR-004, SC-005)**: before insert into `tools`, resolve via normalized name + rapidfuzz ≥ threshold or canonical-domain match; on match, attach candidate to existing tool and append to `source_refs`. UNIQUE `(report_id, tool_id)` enforces zero in-report duplicates.
- **Exclusion (FR-005)**: a candidate set to `validation_status='excluded'` MUST have `exclusion_reason`.
- **Popularity (FR-006)**: candidate qualifies only if its normalized popularity ≥ `config_snapshot.popularity_threshold`.
- **Source traceability (SC-006)**: every `tools.source_refs` entry references at least one verifiable candidate/source.
- **Report completeness (FR-013)**: `reports.sections` MUST contain the eight required sections in order; checked before `status='succeeded'`.
- **Secret safety (FR-027/SC-011)**: no column stores secrets; `run_steps.detail` and logs pass through redaction.

## Retention

v1 default: **retain all** runs, reports, profiles, and tool history indefinitely (supports FR-018–020 history & comparison). A future retention policy can prune `candidates` (raw audit data) older than N days without affecting reports or tool history.
