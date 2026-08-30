# V3 Rollout

## 1. Copy this update over the existing repository
Replace matching files. Do not delete your existing `data/models/` folder.

## 2. Verify locally from the repository root

```bash
python -m pytest -q
```

Expected: `12 passed`.

Optional frontend syntax check:

```bash
node --check frontend/src/App.js
node --check frontend/src/api.js
```

## 3. Push the update

```bash
git status
git add .
git commit -m "Upgrade BTC Agent to V3 autonomous research"
git push
```

GitHub Actions rebuilds Pages and Render auto-deploys the backend.

## 4. Verify deployed backend

Open:

`https://leejaehoon1234-btc-agent-api.onrender.com/health`

Expected fields include:

```json
{
  "status": "ok",
  "version": "3.0.0",
  "model_available": true,
  "llm_available": false,
  "skill_count": 6
}
```

Then verify:

`https://leejaehoon1234-btc-agent-api.onrender.com/api/v1/skills`

## 5. Verify deployed frontend

`https://LeeJaeHoon1234.github.io/btc-agent/`

The header should display `BTC Agent V3` and the page should include a Research Question input, Planner, Research Synthesis, Specialist panels, and Evidence Registry.

## 6. Enable actual LLM agents after V3 works with LLM off

In Render > Environment add/change:

```text
USE_LLM=true
USE_SPECIALIST_LLM=true
OPENAI_MODEL=gpt-5.6-terra
OPENAI_API_KEY=<server-side secret>
```

Optional macro source:

```text
FRED_API_KEY=<your FRED key>
```

After saving, Render redeploys automatically.
