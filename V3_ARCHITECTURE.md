# BTC Agent V3 Architecture Notes

## What Changed from V2

V2 was primarily deterministic orchestration: every predefined module ran in a fixed sequence and the LLM was used only for selected deep-analysis / explanation steps.

V3 adds a research control plane above that engine:

1. `Planner Agent` reads the research question.
2. `SkillRegistry` loads specialist `SKILL.md` files.
3. Planner selects only relevant specialists.
4. Specialist tools run in parallel where possible.
5. News and historical data pass through retrieval before synthesis.
6. Evidence is stored in a structured registry.
7. A Research Synthesizer creates a cross-domain thesis.
8. Research influence on deterministic Entry/Exit scores is bounded.
9. Material disagreement forces `deep_analysis`.
10. Existing Risk / Decision / Critic / Position layers remain the final control path.

## Main New Files

```text
skills/*/SKILL.md
src/core/v3/skill_registry.py
src/agents/v3/planner_agent.py
src/agents/v3/research_orchestrator.py
src/agents/v3/derivatives_agent.py
src/agents/v3/macro_agent.py
src/agents/v3/news_agent.py
src/agents/v3/historical_agent.py
src/agents/v3/research_synthesizer.py
src/tools/research/derivatives_tool.py
src/tools/research/macro_tool.py
src/tools/research/news_search_tool.py
src/retrieval/text_retriever.py
src/retrieval/historical_rag.py
src/engines/research_engine.py
```

## Backward Compatibility

- Existing `btc_lgbm.joblib` path is unchanged.
- Existing Upbit core market-data path is unchanged.
- `/api/v1/analyze` remains the main endpoint; it now accepts an optional `question`.
- Demo mode exercises the full V3 routing without external network calls.
- The existing GitHub Pages + Render deployment model remains unchanged.
