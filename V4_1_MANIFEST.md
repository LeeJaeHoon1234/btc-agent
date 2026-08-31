# V4.1 Manifest

Primary V4.1 changes:

- `frontend/src/App.jsx` — dual-currency hero, readable live cards, day-range visualization, expandable/zoomable chart, memory UI.
- `frontend/src/styles.css` — V4.1 responsive UI.
- `src/tools/live_market.py` — USD reference, 60m series, corrected daily-change semantics, friendly context, sanity validation.
- `src/memory/prediction_journal.py` — horizon prediction journal, outcome resolution, performance matrix.
- `src/agents/v4/reflection_agent.py` — optional bounded LLM reflection.
- `src/agents/v4/autonomy_agent.py` — specialist independence + weak memory prior.
- `src/core/orchestrator.py` — V4.1 reflection and journal orchestration.
- `backend/main.py` — API version 4.1.0 and `/api/v1/journal`.
- `backend/serializers.py`, `src/core/state.py` — memory/reflection API fields.
- `tests/test_v41.py` plus updated API/core contracts.

Validation: `23 passed`.
