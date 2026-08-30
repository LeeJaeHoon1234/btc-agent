$ErrorActionPreference = "Stop"
$env:USE_LLM = "false"

python -m compileall -q .
pytest -q
node --check frontend/src/App.js
node --check frontend/src/api.js
node --check frontend/src/main.js
node --check frontend/vite.config.js

Write-Host "Backend tests and frontend syntax checks passed." -ForegroundColor Green
