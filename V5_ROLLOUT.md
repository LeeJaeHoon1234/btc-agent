# BitScope V5 Rollout

## Release

`5.0.0`

## Upgrade strategy

V5 is built on the V4.1.1 repository and keeps the existing FastAPI and React surfaces. Backward-facing horizon/user-view fields and legacy log aliases remain available, while new V5 fields are additive.

### New response fields

- `facts`
- `deterministic_priors`
- `forecasts`
- `market_state`
- `council`
- `meta_decision`
- `risk_governor`
- `portfolio`
- `track_record`

`POST /api/v1/analyze` also accepts optional:

```json
{"current_exposure_pct": 40}
```

Range: `0..100`.

## Local verification

```bash
python -m pytest -q
python -m compileall -q src backend config
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

## Real-data forecast validation

```bash
python scripts/validate_v5.py --market KRW-BTC --years 8 --points 40
```

Do not promote backtest numbers as live performance. The `/api/v1/journal` track record should be kept on durable storage before public performance claims are shown.

## Deployment

Backend: keep the current Render/Docker deployment and environment variables.

Frontend: keep the current GitHub Pages workflow and set `VITE_API_BASE_URL` to the Render API origin.

Recommended sequence:

```bash
git checkout -b bitscope-v5
git add .
git commit -m "Upgrade BitScope to V5 decision intelligence"
git push -u origin bitscope-v5
```

After CI passes, merge to the branch used by Render and GitHub Pages.

## Production checks

- `/health` reports `5.0.0`
- Demo analysis includes all V5 fields
- Live price still updates independently of the slow AI layer
- Entering a current BTC exposure changes only the portfolio delta/cache key, not market facts
- Risk Governor approved exposure is never above proposed exposure
- Journal is backed by persistent disk/database before using public track-record statistics
