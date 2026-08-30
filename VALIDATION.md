# Validation Record

Validation performed during reconstruction/migration.

## Passed locally

- `python -m compileall -q .`
- `node --check frontend/src/App.js`
- `node --check frontend/src/api.js`
- `node --check frontend/src/main.js`
- `node --check frontend/vite.config.js`
- YAML parse: `render.yaml`
- YAML parse: `.github/workflows/deploy-pages.yml`
- YAML parse: `.github/workflows/test.yml`
- `USE_LLM=false pytest -q` -> **7 passed**
- Real local Uvicorn process -> `GET /health` -> **HTTP 200**
- Real local Uvicorn process -> `POST /api/v1/analyze` with `source=demo` -> **HTTP 200**
- End-to-end demo result observed: action `관망`, Entry 67.55, Exit 3.58, route `deep_analysis`, 15 execution steps, 120 chart points.
- LightGBM test: synthetic feature dataset -> train -> joblib save -> metadata save -> reload -> probability inference.
- API test: upstream connection failure -> **HTTP 502** mapping.
- API test: browser CORS preflight from `http://localhost:5173` -> **HTTP 200**.

## Environment-limited checks

### Upbit live request

The execution container cannot resolve external DNS, so the live Upbit request could not be validated here. The observed exception was a DNS `NameResolutionError`, not an Agent code error. The API converts upstream request failures to HTTP 502.

### `npm run build`

The execution container also cannot reach the npm registry, so React/Vite dependencies could not be installed locally. JavaScript/Vite config syntax was checked with Node, and the included GitHub Actions workflow performs a real `npm install` + `npm run build` on every push/PR in a network-enabled GitHub runner.

Do not interpret those two environment restrictions as successful external-integration tests; verify the green GitHub Actions run and one `source=live` request after deployment.
