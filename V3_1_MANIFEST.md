# V3.1 update manifest

Core changes:

- `src/core/v3/usage_guard.py` — IP request rate limits, daily LLM reservations, request-scoped call/token budget, anonymous client hashing.
- `src/agents/llm_client.py` — integrates request-scoped LLM budget and records provider token usage when available.
- `src/agents/v3/research_orchestrator.py` — propagates the same request budget into parallel specialist threads.
- `backend/service.py` — cache-aware LLM reservation/fallback and usage metadata.
- `backend/main.py` — V3.1 API, IP guard, 429 response, `/api/v1/usage`.
- `frontend/src/api.js` / `frontend/src/App.js` / `frontend/src/styles.css` — public quota visibility and fallback badges.
- `config/settings.py`, `.env.example`, `render.yaml` — configurable guardrail defaults.
- `tests/v3/test_usage_guard.py` and API contract tests.

The update patch intentionally excludes `data/models/` so the deployed LightGBM artifact is not overwritten.
