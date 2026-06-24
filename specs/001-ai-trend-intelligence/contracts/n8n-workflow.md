# n8n Orchestration Workflow Contract

One primary workflow, **`trend-intelligence-run`**, drives a full pipeline as a tracked background job (FR-015). It calls the FastAPI stage endpoints in sequence with explicit error branches and bounded retries. n8n owns scheduling, retries, and error routing; FastAPI owns the work and the `runs`/`run_steps` audit trail.

## Triggers (FR-016)

- **Schedule Trigger** — default weekly (cron configurable in the node). Path A.
- **Webhook Trigger** (`POST /webhook/trend-run`) — manual/on-demand. Path B.

Both paths converge on a **Create Run** node.

## Node sequence

```text
[Schedule Trigger]──┐
                    ├──► (1) HTTP: POST /runs {trigger_type}            ──► capture run_id
[Webhook Trigger]──┘
   │
   ▼
(2) HTTP: POST /runs/{run_id}/discover
   │   └─(error)─► [Mark Run Failed] ─► [Notify] ─► (end)
   ▼
(3) HTTP: POST /runs/{run_id}/validate
   │   ├─(no_trends == true)─► [Log no_trends outcome] ─► (end, FR-026)
   │   └─(error)─────────────► [Mark Run Failed] ─► (end)
   ▼
(4) HTTP: POST /runs/{run_id}/analyze
   │   └─(error)─► [Mark Run Failed] ─► (end)
   ▼
(5) HTTP: POST /runs/{run_id}/report
   │   └─(error)─► [Mark Run Failed] ─► (end)
   ▼
(6) HTTP: GET /runs/{run_id}            ──► assert status in {succeeded, partial}
   ▼
(7) [Notify success: report_id, pdf path]  (end)
```

## Node-level settings

| Node | Method/URL | Retry | Timeout | On error |
|------|-----------|-------|---------|----------|
| Create Run | `POST /runs` | 2 | 30s | stop+fail |
| Discover | `POST /runs/{id}/discover` | 1 | 120s | → Mark Failed branch |
| Validate | `POST /runs/{id}/validate` | 1 | 60s | → Mark Failed / check `no_trends` |
| Analyze | `POST /runs/{id}/analyze` | 1 | 900s | → Mark Failed branch |
| Report | `POST /runs/{id}/report` | 1 | 300s | → Mark Failed branch |
| Status check | `GET /runs/{id}` | 2 | 30s | → Mark Failed branch |

- **Base URL**: `http://api:8000` (Docker service DNS).
- **Auth**: optional API-key header (n8n credential) — matches the FastAPI API-key dependency.
- Retries here are n8n's node-level retries; FastAPI also performs its own bounded provider retries internally (FR-025). The two are complementary, not duplicative (n8n retries the HTTP call; FastAPI retries the OpenRouter call).
- The "Mark Run Failed" node calls back into the API (or simply relies on FastAPI having already set `failed`) and routes to a notify node. The notify node is a placeholder (log/no-op in v1; email/Slack out of scope).

## Versioning & export

- Workflow exported as JSON to `n8n/workflows/trend-intelligence-run.json` and imported on first boot (documented in quickstart.md).
- Granularity rationale: separate stage calls (not one mega-endpoint) so the operator sees per-stage progress in n8n's execution view and can resume/retry a single failed stage during development. This mirrors the per-step rows in `run_steps`.
