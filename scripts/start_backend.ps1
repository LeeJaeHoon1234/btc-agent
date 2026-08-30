$ErrorActionPreference = "Stop"
if (-not $env:USE_LLM) {
    $env:USE_LLM = "false"
}
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
