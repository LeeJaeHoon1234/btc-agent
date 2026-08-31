# BTC Agent V4.1 Rollout

V4.1 is an in-place update for the existing BTC Agent repository.

## 1. Back up the current V4 branch

```bash
git checkout -b backup-v4
git push -u origin backup-v4
git checkout main
```

## 2. Preserve the saved model

Do not delete:

```text
data/models/btc_lgbm.joblib
data/models/btc_lgbm_metadata.json
```

Copy the V4.1 update ZIP over the repository root.

## 3. Recommended Render environment

Keep the existing OpenAI secret server-side. Recommended values remain:

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

Optional durable journal path if a persistent disk is mounted:

```text
PREDICTION_JOURNAL_PATH=/var/data/btc-agent/prediction_journal.json
```

Without a persistent disk, reflection memory is process/filesystem-local and may reset after a Render restart/redeploy.

## 4. Verify backend

```bash
python -m pytest -q
```

Expected:

```text
23 passed
```

Check:

```text
GET /health            -> version 4.1.0
GET /api/v1/live       -> KRW + USD reference + friendly + validation + 1m/5m/60m series
GET /api/v1/journal    -> records/reflections/memory
POST /api/v1/analyze   -> NOW/TODAY/1W/1M/1Y + memory/reflection fields
```

## 5. Verify frontend

```bash
cd frontend
npm install
npm run build
```

Expected visible changes:

- `BTC Agent V4.1` header
- BTC/KRW plus BTC/USD reference price
- `전일 종가 대비` instead of incorrectly implying the exchange daily change is rolling 24h
- readable 1H/4H cards with mini charts
- day low/current/high range bar
- enlarged chart modal with 1H/4H/1D/3D, hover and zoom
- data consistency warning when values conflict
- Reflection Memory under Detailed analysis

## 6. Commit and deploy

```bash
git status
git add .
git commit -m "Upgrade BTC Agent to V4.1 reflection and readable live UI"
git push
```

GitHub Actions should rebuild Pages and Render should redeploy the backend.

## Validation note for this package

- Python compilation: passed
- Backend/API test suite: `23 passed`
- Frontend JSX/JS syntax: passed via TypeScript parser
- `npm install` could not complete in the artifact environment because the npm registry was unreachable; no new frontend dependency was added, so the existing React/Vite dependency set is unchanged.
