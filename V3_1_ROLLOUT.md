# BTC Agent V3.1 rollout

V3.1 is an in-place update for the existing `btc-agent-web-LeeJaeHoon1234` repository.

## What changes

- Public request rate limit: 6/IP/hour, 10/IP/day.
- Public LLM quota: 3 LLM-enabled analyses/IP/day.
- Service LLM quota: 30 LLM-enabled analyses/day.
- Request-scoped LLM budget: at most 8 calls and 30,000 observed tokens per analysis.
- Quota exhaustion does **not** kill analysis: Rule/ML fallback remains active.
- Live cache hits reuse the previous result and report `cache_hit_no_new_llm_cost`.
- `/api/v1/usage` exposes anonymous quota counters for the current visitor.
- UI shows AI quota state and whether the result used LLM, cache, or Rule/ML fallback.
- Raw client IPs are not stored; the process keeps a short SHA-256-derived key only.

## Copy and test

Copy the contents of the V3.1 update ZIP over the existing project root. Do not delete `data/models/`.

```bash
python -m pytest -q
```

Expected:

```text
17 passed
```

Then:

```bash
git status
git add .
git commit -m "Upgrade BTC Agent to V3.1 cost guard"
git push
```

## Render environment

Keep the OpenAI key only in Render. Recommended values:

```text
USE_LLM=true
USE_SPECIALIST_LLM=true
COST_GUARD_ENABLED=true
IP_HOURLY_REQUEST_LIMIT=6
IP_DAILY_REQUEST_LIMIT=10
IP_DAILY_LLM_ANALYSIS_LIMIT=3
GLOBAL_DAILY_LLM_ANALYSIS_LIMIT=30
MAX_LLM_CALLS_PER_ANALYSIS=8
MAX_LLM_TOKENS_PER_ANALYSIS=30000
```

`OPENAI_API_KEY` remains a Render secret and must never be committed.

## Verify after deploy

`/health` should contain:

```json
{"status":"ok","version":"3.1.0","llm_available":true,"cost_guard_enabled":true}
```

`/api/v1/usage` should show request and LLM quota counters.

> The built-in counters are process-memory guardrails. A Render restart resets them, so keep provider-side billing controls/alerts as the hard financial backstop.
