# BitScope web architecture

## Production surfaces

```text
Browser
  -> React + Vite on GitHub Pages
  -> FastAPI JSON API on Render
  -> market and research data providers
```

The browser renders API results and subscribes to Upbit for fast price updates. Investment calculations and agent orchestration remain in the backend.

## Backend flow

```text
Market data
  -> validation and freshness checks
  -> deterministic indicators and market state
  -> historical outcome distributions
  -> independent specialist agents
  -> bounded meta decision
  -> deterministic risk governor
  -> portfolio guidance and prediction journal
```

The system does not load or train a predictive model. Python owns numeric calculations, while language agents interpret supplied evidence and challenge unsupported conclusions.

## Frontend flow

`frontend/src/App.jsx` renders the five horizon views, portfolio guidance, data health, council views, forecast distributions, and track record. `frontend/src/api.js` is the only HTTP boundary.

GitHub Pages deployment is defined in `.github/workflows/deploy-pages.yml`. The backend URL is injected through `VITE_API_BASE_URL` during the build.
