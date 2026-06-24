# AI Trend Intelligence Platform

A self-hosted platform that automatically discovers trending technologies, runs multi-agent AI analysis via [OpenRouter](https://openrouter.ai/), and generates premium Markdown + PDF research reports.

## Architecture

```
n8n (orchestration) → FastAPI (discovery → validation → analysis → reporting) → PostgreSQL + file storage
```

Three Docker Compose services: `api` (port 127.0.0.1:8000), `n8n` (port 127.0.0.1:5678), `postgres`.

## Quick Start

### 1. Configure

```bash
cp .env.example .env
# Edit .env — required:
#   OPENROUTER_API_KEY=sk-or-...
#   OPENROUTER_DEFAULT_MODEL=anthropic/claude-3-haiku
#   POSTGRES_PASSWORD=changeme
#   N8N_ENCRYPTION_KEY=changeme_32char_key
#   N8N_BASIC_AUTH_PASSWORD=changeme
```

### 2. Launch

```bash
docker compose up -d
docker compose exec api alembic upgrade head
curl http://localhost:8000/health
```

### 3. Import the n8n workflow

1. Open http://localhost:5678 and log in (use `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD`)
2. Go to **Workflows** → **Import** → upload `n8n/workflows/trend-intelligence-run.json`
3. Activate the workflow

### 4. Enable discovery sources

```bash
# Hacker News (no auth needed)
curl -X POST http://localhost:8000/config/sources \
  -H 'Content-Type: application/json' \
  -d '{"key":"hackernews","type":"api","display_name":"Hacker News","enabled":true,"config":{}}'
```

### 5. Trigger a run

```bash
# Create run
RUN=$(curl -s -X POST http://localhost:8000/runs \
      -H 'Content-Type: application/json' \
      -d '{"trigger_type":"manual"}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Trigger via n8n webhook
curl -X POST http://localhost:5678/webhook/trend-run -d "{\"run_id\":\"$RUN\"}"

# Poll status
curl http://localhost:8000/runs/$RUN | python -m json.tool
```

## Design Docs

- [Specification](../specs/001-ai-trend-intelligence/spec.md)
- [Architecture Plan](../specs/001-ai-trend-intelligence/plan.md)
- [Data Model](../specs/001-ai-trend-intelligence/data-model.md)
- [API Contract](../specs/001-ai-trend-intelligence/contracts/openapi.yaml)
- [Agent Contracts](../specs/001-ai-trend-intelligence/contracts/agents.md)
- [n8n Workflow Contract](../specs/001-ai-trend-intelligence/contracts/n8n-workflow.md)
- [Adding a Source](docs/adding-a-source.md)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | n8n |
| API | Python 3.12 + FastAPI |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async + Alembic |
| AI | OpenRouter (via OpenAI SDK) |
| PDF | WeasyPrint + Jinja2 + markdown-it-py |
| Dedup | rapidfuzz |
| Discovery | httpx + feedparser + trafilatura + selectolax |
| Retry | tenacity |
| Logging | structlog (secrets redacted) |

## Security

- All secrets via `.env` only — never committed, never logged, never stored
- Service ports bind to `127.0.0.1` (localhost only)
- Non-root Docker user (`appuser`)
- URL scheme allowlist + fetch size caps
- Secret-redaction structlog processor verified by unit tests

## Teardown

```bash
docker compose down          # keep data
docker compose down -v       # also drop volumes
```
