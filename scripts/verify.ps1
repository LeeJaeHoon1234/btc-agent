$ErrorActionPreference = "Stop"
$env:USE_LLM = "false"

python -m compileall -q .
pytest -q
Push-Location frontend
try {
    npm.cmd install --no-audit --no-fund
    npm.cmd run build
}
finally {
    Pop-Location
}

Write-Host "Backend tests and frontend production build passed." -ForegroundColor Green
