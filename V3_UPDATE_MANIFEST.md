# BTC Agent V3 Update Manifest

Extract this package over the existing `btc-agent` repository root and replace matching files.

**The update package intentionally contains no `data/models/` directory**, so your existing `btc_lgbm.joblib` and metadata are preserved.

## V3 additions
- Runtime-loaded specialist `SKILL.md` definitions
- Planner Agent with LLM routing + deterministic fallback
- Parallel specialist research orchestration
- Binance derivatives research
- Macro research (FRED optional + public fallback)
- Recent-news search and TF-IDF retrieval
- Historical market-state RAG
- Research Synthesizer
- Structured Evidence Registry
- Bounded research adjustment (max ±8 Entry points)
- Core/research disagreement escalation to Deep Analysis
- V3 API contract and `/api/v1/skills`
- V3 React UI
- V3 regression tests

## Deployment compatibility
- Existing GitHub Pages frontend path is preserved.
- Existing Render backend service can continue auto-deploying from `main`.
- Dockerfile retains the `libgomp1` fix required by LightGBM on Render.
