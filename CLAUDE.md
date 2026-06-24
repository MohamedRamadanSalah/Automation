<!-- SPECKIT START -->
## Active Feature: AI Trend Intelligence Platform (`001-ai-trend-intelligence`)

For technologies, project structure, shell commands, and design context, read the current plan and its Phase 0/1 artifacts:

- Plan: `specs/001-ai-trend-intelligence/plan.md`
- Research (tech decisions): `specs/001-ai-trend-intelligence/research.md`
- Data model / schema: `specs/001-ai-trend-intelligence/data-model.md`
- Contracts: `specs/001-ai-trend-intelligence/contracts/` (`openapi.yaml`, `agents.md`, `n8n-workflow.md`)
- Quickstart / validation: `specs/001-ai-trend-intelligence/quickstart.md`

**Stack**: Python 3.12 + FastAPI, SQLAlchemy 2.0 async + asyncpg + Alembic, PostgreSQL 16,
n8n (orchestration), OpenRouter via OpenAI SDK, WeasyPrint (PDF), rapidfuzz/feedparser/trafilatura,
all run via Docker Compose (`api` + `n8n` + `postgres`). Single-operator local deployment.
<!-- SPECKIT END -->
