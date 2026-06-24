# Adding a New Discovery Source

A discovery source is a pluggable adapter that implements the `SourceAdapter` protocol.
Adding a new source requires changes only to the adapter module and configuration — no changes to unrelated layers (Modularity principle, FR-023).

## Steps

### 1. Implement the adapter

Create `app/src/trend_intel/discovery/sources/{key}.py`:

```python
from typing import Any
from trend_intel.discovery.base import CandidateDTO
from trend_intel.core.errors import SourceError

class MySourceAdapter:
    key = "my_source"  # unique, lowercase, no spaces

    async def fetch(self, config: dict[str, Any]) -> list[CandidateDTO]:
        # Fetch candidates, return [] on partial failure, raise SourceError on total failure
        ...
```

### 2. Register the adapter

In `app/src/trend_intel/discovery/registry.py`, import and add to `_BUILTIN_ADAPTERS`:

```python
from trend_intel.discovery.sources.my_source import MySourceAdapter

_BUILTIN_ADAPTERS = {
    ...
    "my_source": MySourceAdapter(),
}
```

### 3. Add the source record via API

```bash
curl -X POST http://localhost:8000/config/sources \
  -H 'Content-Type: application/json' \
  -d '{
    "key": "my_source",
    "type": "api",
    "display_name": "My Source",
    "enabled": true,
    "config": {"limit": 20, "timeout": 15}
  }'
```

The source will participate in the next discovery run with no code changes to other layers.

## CandidateDTO fields

| Field | Type | Notes |
|-------|------|-------|
| `raw_name` | str | Tool/item name as seen at source |
| `source_key` | str | Must match adapter.key |
| `url` | str? | Item URL |
| `canonical_domain` | str? | For URL-based dedup |
| `raw_signals` | dict | Popularity signals (stars, votes, etc.) |
| `discovered_at` | datetime | UTC timestamp |

## Tips

- Return `[]` if credentials are missing (optional sources like Reddit/ProductHunt)
- Raise `SourceError` only on a total failure — the orchestration layer skips and continues
- Never store credentials in `discovery_sources.config` — use env variables and pass via `config` dict from env
- Write a fixture-based unit test in `app/tests/unit/test_adapters.py`
