# BTC Agent final deployment — LeeJaeHoon1234

Target architecture:

- Frontend: `https://LeeJaeHoon1234.github.io/btc-agent/`
- Backend: Render FastAPI public URL (`https://...onrender.com`)
- GitHub repository: `https://github.com/LeeJaeHoon1234/btc-agent`

## 0. Before pushing: production ML artifact

The deployed backend can use the trained LightGBM model only if these files are inside this project before the Git push:

- `data/models/btc_lgbm.joblib`
- `data/models/btc_lgbm_metadata.json`

Verify in PowerShell from project root:

```powershell
Get-ChildItem .\data\models\
python -c "from config.settings import MODEL_PATH; print(MODEL_PATH); print(MODEL_PATH.exists())"
```

The final line must be `True` if you want ML enabled in production.

This deployment-ready version intentionally allows the two production model artifacts to be committed. Do not commit API keys or `.env`.

## 1. Create and push GitHub repository

Create a PUBLIC repository named exactly `btc-agent` under `LeeJaeHoon1234`.
Do not initialize it with another README/.gitignore if this local project already has files.

From this project root:

```powershell
git init
git branch -M main
git add .
git status
git commit -m "Deploy BTC Agent web service"
git remote add origin https://github.com/LeeJaeHoon1234/btc-agent.git
git push -u origin main
```

If `origin` already exists:

```powershell
git remote set-url origin https://github.com/LeeJaeHoon1234/btc-agent.git
git push -u origin main
```

Before the commit, verify `git status` lists `data/models/btc_lgbm.joblib` if that file exists locally.

## 2. Deploy FastAPI backend to Render FIRST

In Render:

1. New -> Web Service.
2. Connect GitHub repo `LeeJaeHoon1234/btc-agent`.
3. Branch: `main`.
4. Runtime: Python 3.
5. Build command: `pip install -r requirements.txt`
6. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
7. Set Python version to `3.12.11` if Render does not pick up `.python-version`.
8. Set environment variable:
   - `CORS_ORIGINS=https://LeeJaeHoon1234.github.io,http://localhost:5173,http://127.0.0.1:5173`
   - `USE_LLM=false` initially.
   - `OPENAI_MODEL=gpt-5.6`
   - `ANALYSIS_CACHE_TTL_SECONDS=300`
9. Health check path: `/health`.
10. Deploy.

This repository also has `render.yaml` with the equivalent settings.

When deployment completes, open:

```text
https://YOUR-RENDER-URL.onrender.com/health
https://YOUR-RENDER-URL.onrender.com/docs
```

`/health` should show `status: ok`. If the model was committed, `model_available` should be `true`.

## 3. Tell GitHub Pages which backend URL to call

In GitHub repo:

Settings -> Secrets and variables -> Actions -> Variables -> New repository variable

Name:

```text
VITE_API_BASE_URL
```

Value:

```text
https://YOUR-RENDER-URL.onrender.com
```

No trailing `/` is needed.

## 4. Enable GitHub Pages

GitHub repo:

Settings -> Pages -> Build and deployment -> Source -> `GitHub Actions`

Then go to Actions -> `Deploy React frontend to GitHub Pages` -> Run workflow.

The Vite config automatically derives `/btc-agent/` from `GITHUB_REPOSITORY`, so the expected site URL is:

```text
https://LeeJaeHoon1234.github.io/btc-agent/
```

## 5. Final verification

Open the GitHub Pages URL and verify the top badge says `API online`.

Then test:

1. Demo analysis -> result cards render.
2. Live analysis -> Upbit live data returns.
3. ML status -> `ready` if the joblib model was committed.
4. Render `/health` -> `model_available: true`.
5. Browser devtools console -> no CORS errors.

## 6. Turn on conditional LLM later

Do this only on the Render backend. Never put an API key into React/GitHub Pages.

Render environment variables:

```text
USE_LLM=true
OPENAI_MODEL=gpt-5.6
OPENAI_API_KEY=<your API key>
```

After saving, redeploy/restart. The OpenAI API key is separate from a ChatGPT subscription and should remain server-side only.

## 7. Free Render note

If you use Render Free, the backend can spin down after inactivity. The first request after idle may therefore take longer while the service starts again. The frontend itself remains hosted on GitHub Pages.
