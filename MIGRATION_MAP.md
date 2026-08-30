# Streamlit -> React + FastAPI Migration Map

## Preserved domain logic

| Existing file | Web-service role |
|---|---|
| `src/core/state.py` | Shared Agent state |
| `src/core/orchestrator.py` | Single workflow entry point |
| `src/tools/market_data.py` | Upbit daily candles |
| `src/tools/indicators.py` | RSI/MA/volume/returns/features |
| `src/tools/ml_predictor.py` | Saved LightGBM inference |
| `src/tools/regime_tool.py` | Market regime |
| `src/tools/similarity_tool.py` | Historical analog search |
| `src/tools/cycle_tool.py` | Cycle/top-risk proxy inputs |
| `src/engines/entry_engine.py` | Entry score |
| `src/engines/exit_engine.py` | Exit/top-risk score |
| `src/engines/confidence_gate.py` | Fast/deep route |
| `src/engines/position_engine.py` | Position-size suggestion |
| `src/agents/technical_agent.py` | Technical interpretation |
| `src/agents/cycle_agent.py` | Cycle interpretation |
| `src/agents/risk_agent.py` | Risk synthesis |
| `src/agents/decision_agent.py` | Final action draft/revision |
| `src/agents/critic_agent.py` | Deep-analysis critique |
| `src/agents/explanation_agent.py` | Human-readable output |
| `src/agents/llm_client.py` | Server-side LLM only |

## New web layer

| New file | Purpose |
|---|---|
| `backend/main.py` | FastAPI routes, validation, CORS, errors |
| `backend/service.py` | Orchestrator service + TTL cache |
| `backend/serializers.py` | Strict JSON-safe AgentState conversion |
| `src/tools/demo_data.py` | Offline deterministic end-to-end smoke data |
| `frontend/src/App.js` | React dashboard |
| `frontend/src/api.js` | HTTP client |
| `.github/workflows/deploy-pages.yml` | GitHub Pages deployment |
| `.github/workflows/test.yml` | Backend tests + frontend production build in CI |

## Important design rule

React never imports or reimplements trading logic. It only renders the JSON contract from FastAPI. This prevents the Streamlit-to-web migration from silently changing the investment logic.
