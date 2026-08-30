# BTC Agent Web Service

기존 `btc_agent_v2`의 Rule + LightGBM + Confidence Gate + conditional LLM 구조를 그대로 유지하면서, Streamlit 전용 UI와 Agent 두뇌를 분리한 웹서비스 버전입니다.

## Architecture

```text
GitHub Pages / React
        |
        | HTTPS JSON
        v
FastAPI backend
        |
        v
BTCAgentOrchestrator
  |-- market_data.py (Upbit)
  |-- indicators.py
  |-- technical_agent.py
  |-- ml_predictor.py -> saved LightGBM
  |-- regime_tool.py
  |-- similarity_tool.py
  |-- cycle_tool.py
  |-- entry_engine.py / exit_engine.py
  |-- confidence_gate.py
  |-- risk_agent.py
  |-- decision_agent.py
  |-- critic_agent.py (deep_analysis only)
  |-- position_engine.py
  `-- explanation_agent.py
```

기존 Streamlit `app.py`와 CLI `main.py`도 남겨두었기 때문에 웹 이전 전/후 동작을 비교할 수 있습니다.

## 1. Backend local run

Python 3.11+ 권장.

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements-dev.txt
copy .env.example .env   # Windows cmd; 필요 시 직접 환경변수 설정
uvicorn backend.main:app --reload
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### Live analysis

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"market":"KRW-BTC","history_years":8,"source":"live"}'
```

### Offline/demo analysis

외부 API가 막힌 환경에서도 동일한 전체 Agent 파이프라인을 검증할 수 있습니다.

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"market":"KRW-BTC","history_years":8,"source":"demo"}'
```

## 2. LightGBM model

런타임에서 재학습하지 않습니다. 기존 설계대로 offline training 후 저장 모델을 로드합니다.

```bash
python scripts/train_model.py
```

생성 파일:

```text
data/models/btc_lgbm.joblib
data/models/btc_lgbm_metadata.json
```

모델 파일이 없더라도 API는 죽지 않습니다. ML component는 unavailable 상태로 표시되고 기존 neutral fallback이 적용됩니다.

## 3. Optional LLM

기본값은 `USE_LLM=false`로 시작하는 것을 권장합니다. Rule/ML 파이프라인을 먼저 검증한 뒤 켭니다.

```text
USE_LLM=true
OPENAI_API_KEY=...
OPENAI_MODEL=...
```

LLM은 기존 설계대로 deep-analysis/revision 및 explanation에만 사용되며, API key는 React 쪽에 절대 넣지 않습니다.

## 4. React local run

```bash
cd frontend
npm install
# .env 생성
# VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

브라우저: `http://localhost:5173`

URL query로 API 주소를 임시 override할 수도 있습니다.

```text
http://localhost:5173/?api=https://your-api.example.com
```

## 5. Tests

```bash
pytest -q
```

테스트 범위:

- 전체 Agent orchestration (offline deterministic candles)
- FastAPI health/API response contract
- strict JSON serialization (NaN/Infinity 제거)
- LightGBM train -> save -> load -> inference

외부 Upbit/LLM 호출은 테스트 성공 조건으로 두지 않아 CI가 네트워크 상황에 따라 깨지지 않게 했습니다.

## 6. Deploy backend

### Render

`render.yaml`이 포함되어 있습니다. 저장소를 Render에 연결하고 Web Service로 배포합니다.

배포 후 환경변수를 설정합니다.

```text
CORS_ORIGINS=https://YOUR_GITHUB_ID.github.io
USE_LLM=false
```

LLM을 사용할 때만 서버 Secret에 `OPENAI_API_KEY`를 넣습니다.

Docker/Railway 계열에서도 root의 `Dockerfile` 또는 `Procfile`로 동일하게 실행할 수 있습니다.

## 7. Deploy React to GitHub Pages

GitHub 저장소 Settings -> Pages -> Source를 **GitHub Actions**로 설정합니다.

Repository variable을 추가합니다.

```text
VITE_API_BASE_URL=https://YOUR_BACKEND_HOST
```

`main`에 push하면 `.github/workflows/deploy-pages.yml`이 `frontend`를 build해 Pages로 올립니다. `vite.config.js`는 `GITHUB_REPOSITORY`에서 repo 이름을 읽어 `/repo-name/` base path를 자동 설정합니다.

## 8. CORS

FastAPI는 서로 다른 frontend/backend origin을 명시적으로 허용합니다. 배포 주소가 정해지면 backend 환경변수에 정확한 Pages origin을 추가하세요.

```text
CORS_ORIGINS=http://localhost:5173,https://YOUR_GITHUB_ID.github.io
```

## 9. What is intentionally unchanged

- Rule thresholds and Entry/Exit scoring
- `AgentState` central state pattern
- offline/online LightGBM separation
- Confidence Gate routing
- deep-analysis Critic loop
- final Decision -> Position Engine -> Explanation flow

즉 웹 이전 때문에 투자 판단 로직을 다시 쓰지 않았습니다. UI/HTTP layer만 분리했습니다.

## 10. Next extension points

현재 `exit_engine.py`에 적혀 있는 것처럼 MVRV/LTH/ETF Flow/Funding/OI는 아직 live input으로 연결하지 않았습니다. 다음 버전에서는 이들을 별도 Tool 계층으로 추가하고 `AgentState`에 `derivatives`, `macro`, `flow`를 넣는 방식이 기존 구조와 가장 잘 맞습니다.

## Legacy Streamlit UI

기존 UI도 보존되어 있습니다. 비교 실행이 필요하면:

```bash
pip install -r requirements-legacy.txt
streamlit run app.py
```

---

## LeeJaeHoon1234 production deployment

For the exact GitHub Pages + Render sequence for this repository, see `DEPLOY_GUIDE_LEEJAEHOON1234.md`.
Expected frontend URL when the repository is named `btc-agent`:

`https://LeeJaeHoon1234.github.io/btc-agent/`
