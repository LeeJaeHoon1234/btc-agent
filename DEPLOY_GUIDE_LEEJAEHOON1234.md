# BitScope deployment guide

BitScope has two production surfaces:

- React frontend on GitHub Pages: `https://leejaehoon1234.github.io/btc-agent/`
- FastAPI backend on Render: `https://leejaehoon1234-btc-agent-api.onrender.com`

There is no Streamlit application and no trained-model artifact to deploy.

## GitHub Pages

The workflow `.github/workflows/deploy-pages.yml` builds `frontend/` on every push to `main`.

Set the repository Actions variable `VITE_API_BASE_URL` to the Render origin above. The workflow fails early when this variable is missing.

## Render

Render builds the root `Dockerfile` and starts:

```text
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

The production health check is `/health`. Keep `CORS_ORIGINS` aligned with the GitHub Pages origin.

## Release checks

```powershell
$env:USE_LLM = "false"
pytest -q
Set-Location frontend
npm install --no-audit --no-fund
npm run build
```

After pushing `main`, verify:

1. GitHub Actions tests pass.
2. GitHub Pages deployment succeeds.
3. Render deploys the same commit.
4. `/health` reports the current version.
5. The public site loads live data and a demo analysis.
