# Quickstart: AI Trend Intelligence Platform

End-to-end guide to bring the platform up locally and validate that a report is produced. Implementation details (Compose file contents, code) are produced during `/speckit-implement`; this guide defines the **runnable validation scenarios** and expected outcomes.

## Prerequisites

- Docker + Docker Compose v2
- An **OpenRouter API key** (`OPENROUTER_API_KEY`)
- Optional source credentials (only for sources you enable): Reddit client id/secret, Product Hunt token, GitHub token
- ~2 GB free disk for images + report storage

## 1. Configure

```bash
cp .env.example .env
# edit .env — required:
#   OPENROUTER_API_KEY=sk-or-...
#   OPENROUTER_DEFAULT_MODEL=anthropic/claude-... (shared default; per-role override later)
#   POSTGRES_PASSWORD=...
#   N8N_ENCRYPTION_KEY=...   N8N_BASIC_AUTH_USER/PASSWORD=...
# optional source creds as needed
```

All secrets live only in `.env` (git-ignored). `.env.example` ships placeholders only (FR-027 / SC-011).

## 2. Launch

```bash
docker compose up -d            # starts: api (:8000), n8n (:5678), postgres
docker compose exec api alembic upgrade head     # apply schema
docker compose ps               # all services healthy
curl -s http://localhost:8000/health             # → {"status":"ok","db":"up",...}
```

## 3. Seed sources & import the workflow

```bash
# enable at least Hacker News (no auth) for the MVP smoke test
curl -s -X POST http://localhost:8000/config/sources \
  -H 'content-type: application/json' \
  -d '{"key":"hackernews","type":"api","display_name":"Hacker News","enabled":true,"config":{}}'
```

- Open n8n at `http://localhost:5678`, log in, **import** `n8n/workflows/trend-intelligence-run.json`, and activate it.

## Validation Scenarios

### Scenario A — End-to-end manual run (P1 / SC-001, SC-003)
```bash
RUN=$(curl -s -X POST http://localhost:8000/runs -H 'content-type: application/json' \
      -d '{"trigger_type":"manual"}' | jq -r .id)

# Option 1: trigger via n8n webhook (orchestrated path)
curl -s -X POST http://localhost:5678/webhook/trend-run -d "{\"run_id\":\"$RUN\"}"

# poll status
curl -s http://localhost:8000/runs/$RUN | jq '.status, .outcome'
```
**Expected**: status progresses `discovering→validating→analyzing→reporting→exporting→succeeded`; `outcome=report_generated`.
**Verify the deliverable**:
```bash
REPORT=$(curl -s http://localhost:8000/runs/$RUN | jq -r .report_id)
curl -s http://localhost:8000/reports/$REPORT | jq '.sections'   # all 8 sections, in order
curl -s http://localhost:8000/reports/$REPORT/pdf -o report.pdf  # premium PDF
ls -la storage/reports/$RUN/                                     # report.md + report.pdf
```
**Pass criteria**: PDF opens with cover page, executive summary, table of contents, trend analysis, tool profiles, rankings, recommendations, conclusions — in that order (FR-013).

### Scenario B — Per-step status & error detection (SC-013)
```bash
curl -s http://localhost:8000/runs/$RUN | jq '.steps[] | {step,status,attempts}'
```
**Expected**: every step `succeeded`; on an induced failure (e.g., invalid model id), the failing step shows `failed` with a redacted reason and `runs.failure_reason` is set — no secret values present.

### Scenario C — Validation / dedup (P2 / SC-005, SC-006)
Enable a second source that overlaps (e.g., Dev.to), re-run, then:
```bash
curl -s http://localhost:8000/reports/$REPORT | jq '[.profiles[].canonical_name] | length, (unique|length)'
```
**Pass**: the two counts are equal (zero duplicates). Excluded candidates carry a reason (inspect `validate` stage result).

### Scenario D — Resilience to a failing source (SC-007)
Disable network to one enabled source (or give it a bad endpoint) and run.
**Expected**: run still completes; `skipped_sources` lists the failed source; a report is still produced.

### Scenario E — Historical comparison (P4 / SC-008)
Run twice on different days (or force two runs), then:
```bash
curl -s "http://localhost:8000/reports/compare?base_id=$R1&target_id=$R2" | jq '.new_tools, .dropped_tools, .rank_changes'
curl -s http://localhost:8000/tools/$TOOL/history | jq '.appearances'
```
**Pass**: comparison returns new/dropped/rank-changed within seconds; tool history lists each report + score.

### Scenario F — Configurability (P5 / SC-009)
```bash
curl -s -X PUT http://localhost:8000/config/agents -H 'content-type: application/json' \
  -d '{"role":"ranking","model":"openai/gpt-...","params":{"temperature":0}}'
```
**Pass**: next run uses the new model for the Ranking role only; adding a new RSS source via `POST /config/sources` makes it participate with no code change.

### Scenario G — No qualifying trends (FR-026 / SC-010)
Set `popularity_threshold` impossibly high for a run.
**Expected**: run ends `no_trends` (terminal), no empty report presented as complete.

### Scenario H — Scheduled run (SC-002)
With the workflow active, the Schedule Trigger fires (set a near-term cron to test).
**Expected**: a run completes and a report is stored with no human intervention.

## Teardown
```bash
docker compose down            # keep volumes (history retained)
docker compose down -v         # also drop data + n8n + storage volumes
```

## Mapping to success criteria

| Scenario | Validates |
|----------|-----------|
| A | SC-001, SC-003 |
| B | SC-013 |
| C | SC-005, SC-006 |
| D | SC-007 |
| E | SC-008 |
| F | SC-009 |
| G | SC-010 |
| H | SC-002 |
