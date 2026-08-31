# BTC Agent V4 Rollout

V4 is designed as a safe overlay on the existing `btc-agent` repository.

## 1. Preserve the saved model

Before copying the update, confirm these files still exist in your real repository if you trained them previously:

```text
data/models/btc_lgbm.joblib
data/models/btc_lgbm_metadata.json
```

Do **not** delete them. The V4 update does not require retraining the old 30-day model, and it deliberately treats that model as a supporting signal.

## 2. Overlay V4

Copy the V4 update into the repository root. `frontend/src/main.js` now imports `App.jsx`; the old `App.js` can remain unused or be deleted.

## 3. Render environment

Keep the existing secret:

```text
OPENAI_API_KEY=<server-side secret>
```

Recommended configuration:

```text
USE_LLM=true
USE_SPECIALIST_LLM=true
OPENAI_MODEL=gpt-5.6-terra
ANALYSIS_CACHE_TTL_SECONDS=300
LIVE_SNAPSHOT_CACHE_TTL_SECONDS=10
COST_GUARD_ENABLED=true
IP_HOURLY_REQUEST_LIMIT=6
IP_DAILY_REQUEST_LIMIT=10
IP_DAILY_LLM_ANALYSIS_LIMIT=3
GLOBAL_DAILY_LLM_ANALYSIS_LIMIT=30
MAX_LLM_CALLS_PER_ANALYSIS=8
MAX_LLM_TOKENS_PER_ANALYSIS=30000
```

Optional:

```text
FRED_API_KEY=<your key>
```

## 4. Verify backend locally

```bash
python -m pytest -q
```

Expected:

```text
20 passed
```

Then test:

```text
GET /health
GET /api/v1/live?source=demo
POST /api/v1/analyze {"source":"demo", ...}
```

`/health` must report `4.0.0`.

## 5. Verify frontend

```bash
cd frontend
npm install
npm run build
```

Expected main-page elements:

- BTC Agent V4
- true LIVE/REST/OFFLINE price status
- hold / add / take-profit cards
- NOW / TODAY / 1W / 1M / 1Y tabs
- live event card when a shock/rebound is detected
- data-status chips
- detailed metrics hidden in a collapsed section

## 6. Deploy

```bash
git status
git add .
git commit -m "Upgrade BTC Agent to V4 multi-horizon live intelligence"
git push
```

GitHub Actions builds Pages; Render rebuilds the backend.

## 7. Production checks

After deploy:

1. `/health` -> version `4.0.0`.
2. `/api/v1/live` -> current ticker + intraday metrics, no LLM cost.
3. Dashboard badge becomes `LIVE` only after Upbit WebSocket connects.
4. Full analysis shows five horizon tabs.
5. A Binance block/error should fall back to Bybit when possible instead of making the entire derivatives layer unavailable.
6. Data-status chips must clearly show unavailable sources rather than silently treating them as neutral.

## Local validation note for this generated package

Python compilation and the complete V4 backend test suite were run successfully (`20 passed`). The execution environment used to build this artifact could not reach the npm registry, so `npm install`/Vite build could not be completed locally; the GitHub Actions workflow still installs dependencies and performs the production frontend build after push.
