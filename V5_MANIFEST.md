# BitScope V5 Manifest

## Core

- `src/core/v5/fact_registry.py` — raw facts vs deterministic-prior separation
- `src/engines/v5/forecast_engine.py` — multi-horizon return distributions and probability shrinkage
- `src/engines/v5/regime_engine.py` — structural + acute market-state detector
- `src/agents/v5/council_agent.py` — independent specialist council
- `src/engines/v5/decision_engine.py` — quantitative base allocation
- `src/agents/v5/meta_decision_agent.py` — bounded LLM challenge layer
- `src/engines/v5/risk_governor.py` — hard non-LLM exposure cap/block layer
- `src/engines/v5/portfolio_engine.py` — target/delta/price-anchor plan
- `src/agents/v5/horizon_agent.py` — raw-fact horizon reasoning
- `src/agents/v5/critic_agent.py` — contradiction/citation stress test
- `src/agents/v5/user_writer.py` — plain-language V5 output

## Validation / memory

- `src/validation/v5_walkforward.py` — strict historical truncation validator
- `scripts/validate_v5.py` — real Upbit walk-forward CLI
- `src/memory/prediction_journal.py` — Brier/error/coverage track-record metrics
- `tests/test_v5_architecture.py` — V5 invariants and regression tests
- `validation/v5_demo_walkforward.json` — synthetic validator sanity check, not a profitability result

## API / frontend

- `backend/main.py` — V5 version and optional `current_exposure_pct`
- `backend/service.py` — exposure-aware analysis cache
- `backend/serializers.py` — additive V5 response fields
- `frontend/src/api.js` — exposure input transport
- `frontend/src/App.jsx` — Forecast, Council, Risk Governor, Portfolio, Track Record UI
- `frontend/src/i18n.js` — KR/EN V5 labels
- `frontend/src/styles.css` — V5 responsive layout

## V5.0.1 hotfix

- `src/tools/research/flow_tool.py` — strict Farside final-Total-cell parsing
- `src/agents/v5/council_agent.py` — explicit specialist stance precedence, availability and domain counter-cases
- `frontend/src/App.jsx` / `frontend/src/i18n.js` — normalized plain-language state labels
- `V5_0_1_HOTFIX.md` — correctness and UI hotfix notes

## V5.0.2 hotfix

- `src/core/orchestrator.py` — preserves specialist stance/raw-score fields end-to-end
- `src/tools/research/flow_tool.py` — excludes current New York ETF session from completed evidence
- `src/engines/v4/horizon_engine.py` — latest + five-session ETF fallback prior balancing
- `src/agents/v5/council_agent.py` — separate Macro/News members and clearer technical/domain explanations
- `frontend/src/App.jsx` — unavailable/risk/source-aware council badges
- `frontend/src/i18n.js` — Korean/English council labels and source metadata
- `frontend/src/styles.css` — wider two-column council layout
- `tests/test_v5_architecture.py` — end-to-end stance, ETF provisional-session, domain-split regressions
- `V5_0_2_HOTFIX.md` — release rationale and verification notes
