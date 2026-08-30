# BTC Decision Support Agent

> **Rule × LightGBM × Confidence Gate × Conditional LLM**  
> 단일 모델의 예측에 의존하지 않고, 서로 다른 시장 신호를 구조적으로 결합해 **매수 / 관망 / 비중축소**를 제안하는 BTC 투자 의사결정 보조 Agent입니다.

**Live Service**  
https://LeeJaeHoon1234.github.io/btc-agent/

**FastAPI Docs**  
https://leejaehoon1234-btc-agent-api.onrender.com/docs

---

## 1. Why I Built This

BTC 투자 판단에서 단일 지표나 단일 ML 모델만 사용하는 방식에는 한계가 있다고 판단했습니다.

- RSI나 이동평균 Rule은 **해석이 쉽지만 경계값에 민감**합니다.
- ML은 여러 신호를 동시에 반영할 수 있지만 **항상 신뢰할 수 있는 예측을 주지는 않습니다**.
- LLM은 복잡한 상황을 설명하는 데 강하지만 **숫자 계산과 1차 판단을 맡기기에는 불필요하게 비싸고 비결정적**입니다.

그래서 각 방법의 역할을 분리했습니다.

```text
Rule        → 명확한 기준과 설명 가능성
LightGBM    → Rule이 놓치는 비선형 패턴을 보조
Regime      → 현재 시장 국면을 별도로 판단
Similarity  → 과거 유사구간의 이후 수익률 확인
Cycle       → 장기 과열 / 고점 위험 점검
Confidence Gate
            → 신호가 충분히 일치하면 빠르게 종료
            → 충돌하거나 임계값 근처면 Deep Analysis
Conditional LLM / Critic
            → 필요한 Case에서만 추가 검증
```

핵심 목표는 **“더 복잡한 모델을 만드는 것”이 아니라, 어떤 상황에서 어떤 판단 모듈을 신뢰할지 구조화하는 것**이었습니다.

---

## 2. System Architecture

```text
                         Upbit BTC Daily Data
                                  │
                                  ▼
                         Feature / Indicator Tool
                                  │
             ┌────────────────────┼────────────────────┐
             ▼                    ▼                    ▼
      Technical Agent       LightGBM Model       Market Regime
             │                    │                    │
             └─────────────┬──────┴────────────┬──────┘
                           ▼                   ▼
                    Similarity Tool        Cycle Tool
                           │                   │
                           └─────────┬─────────┘
                                     ▼
                         Entry / Exit Engines
                                     │
                                     ▼
                             Confidence Gate
                              ┌──────┴──────┐
                              │             │
                         Fast Path     Deep Analysis
                              │             │
                              │        Risk / Decision
                              │             │
                              │           Critic
                              │        Revision Loop
                              └──────┬──────┘
                                     ▼
                              Position Engine
                                     │
                                     ▼
                             Final Decision
                                     │
                                     ▼
                            Explanation Agent
                                     │
                                     ▼
                              FastAPI / React
```

모든 모듈은 중앙 `AgentState`를 공유하며, Orchestrator가 실행 순서와 조건부 호출을 제어합니다.

---

## 3. Decision Pipeline

### 3.1 Market Feature Engineering

Upbit 일봉 데이터를 기반으로 시장 상태를 수치화합니다.

주요 Feature:

- RSI 14
- MA20 이격도 / 5일 기울기
- MA200 이격도 / 20일 기울기
- 거래량 비율
- 3일 / 7일 / 30일 / 90일 / 365일 수익률
- ATH 대비 Drawdown
- 30일 변동성
- MA111 / MA350 / Pi-Cycle proxy

단순 가격 자체보다 **추세, 모멘텀, 거래량, 장기 이격도를 분리해서 표현**하도록 구성했습니다.

---

### 3.2 Technical Agent

기술적 시장 상태를 0~100점으로 평가합니다.

예를 들어 다음 조건들을 조합합니다.

- BTC가 MA200 위에 있는가
- MA200 장기 기울기가 상승 중인가
- MA20 단기 추세가 상승 중인가
- RSI가 과열되지 않은 강세 영역인가
- 거래량을 동반한 단기 상승인가

결과는 `bullish / neutral / bearish`와 함께 근거를 반환합니다.

---

### 3.3 LightGBM as a Supporting Signal

ML은 최종 결정을 직접 내리지 않습니다.

현재 LightGBM은 다음 8개 Feature를 사용해 **30일 뒤 BTC 가격 상승 확률**을 추정합니다.

```text
rsi14
ma20_gap_pct
ma20_slope_5d
ma200_gap_pct
ma200_slope_20d
volume_ratio
return_3d_now
return_7d_now
```

모델 평가는 일반 Random Split 대신 **연도 단위 Walk-Forward Validation**으로 수행합니다.

```text
Past Data ──────────────► Future

Train ~ 2022 → Test 2023
Train ~ 2023 → Test 2024
Train ~ 2024 → Test 2025
...
```

또한 웹 요청마다 재학습하지 않고,

```text
Offline Training
Historical Data → Features → Walk-Forward → Final Model → joblib

Online Runtime
Latest Data → Same Features → Saved Model → Probability
```

로 학습과 추론을 분리했습니다.

---

### 3.4 Entry Engine

매수 판단은 하나의 지표가 아니라 네 종류의 신호를 합산합니다.

| Component | Weight |
|---|---:|
| Technical Signal | 35% |
| LightGBM Probability | 25% |
| Market Regime | 20% |
| Historical Similarity | 20% |

최종 `Entry Score`가 높을수록 신규 진입에 우호적인 환경으로 해석합니다.

```text
Entry Score ≥ 70  → Strong Entry
55 ~ 70           → Watch Entry
35 ~ 55           → Neutral
≤ 35              → Avoid Entry
```

ML 모델이 unavailable인 경우 시스템 전체를 중단하지 않고 중립값을 사용하도록 fallback을 설계했습니다.

---

### 3.5 Market Regime & Historical Similarity

#### Regime Detection

가격과 MA20 / MA60 / MA200 배열 및 MA200 기울기를 이용해 시장을 다음과 같이 분류합니다.

```text
bull_trend
bull_transition
sideways
bear_transition
bear_trend
```

같은 RSI 값이라도 상승 추세와 하락 추세에서 의미가 다르기 때문에 **현재 시장 국면을 별도의 판단축으로 분리**했습니다.

#### Similarity Search

현재 시장 Feature Vector와 과거 시장을 표준화한 뒤 유클리드 거리를 계산합니다.

가장 유사했던 과거 `Top-K` 구간을 찾고,

- 당시 이후 30일 평균 수익률
- 상승 비율
- 결과 분산

을 현재 의사결정의 보조 근거로 사용합니다.

---

## 4. Exit Is a Separate Problem

“살 것인가?”와 “이제 팔 것인가?”는 같은 문제라고 보지 않았습니다.

따라서 Entry Engine과 별도로 **Top Risk / Exit Score**를 설계했습니다.

| Exit Component | Max Score |
|---|---:|
| MA200 / MA350 Trend Stretch | 30 |
| Cycle Heat | 25 |
| Momentum Euphoria | 20 |
| Distribution Proxy | 10 |
| Reversal Confirmation | 15 |

이를 통해 단순히 가격이 상승하고 있다는 이유만으로 계속 매수 신호가 유지되는 문제를 방지하고, **사이클 과열과 추세 붕괴를 별도로 평가**합니다.

---

## 5. Confidence Gate: The Core of the Agent

이 프로젝트의 핵심은 모든 분석 모듈을 무조건 실행하는 것이 아니라 **Confidence Gate가 추가 분석의 필요성을 판단하는 것**입니다.

### Fast Path

다음과 같이 신호가 충분히 일치하면 추가 LLM 분석 없이 결정합니다.

```text
Technical ↔ ML 방향 일치
Regime 명확
Entry / Exit 충돌 없음
임계값에서 충분히 떨어져 있음
        ↓
Fast Path
        ↓
Final Decision
```

### Deep Analysis

반대로 아래 Case에서는 판단을 한 번 더 검증합니다.

- Technical과 ML 방향이 충돌
- Entry와 Exit 신호가 동시에 강함
- Entry / Exit Score가 의사결정 임계값 근처
- Regime이 전환 또는 횡보 상태
- 유사구간 결과 분산이 큼
- Walk-Forward AUC가 낮아 ML 신뢰도가 떨어짐

```text
Conflicting Signals
        ↓
Confidence Gate
        ↓
Deep Analysis
        ↓
Risk Agent
        ↓
Decision Agent
        ↓
Critic Agent
        ↓
Revision (max 2 iterations)
```

즉 **LLM은 항상 호출되는 의사결정자가 아니라, 불확실한 Case에서만 사용하는 검증 계층**입니다.

현재 공개 배포 버전은 LLM을 서버에서 선택적으로 On/Off할 수 있으며, LLM이 꺼져 있어도 Rule 기반 fallback으로 전체 Pipeline이 동작합니다.

---

## 6. Final Output

Agent의 최종 출력은 단순한 상승확률이 아닙니다.

```text
Action
→ 매수 / 관망 / 비중축소

Confidence
→ 최종 판단 신뢰도

Position Plan
→ 제안 비중 변화

Entry Score
→ 신규 진입 매력도

Exit Score
→ 사이클 고점 / 과열 위험

Regime
→ 현재 시장 국면

Reasoning
→ 판단 근거와 주의 신호

Invalidation
→ 어떤 조건에서 현재 판단을 다시 평가해야 하는지
```

React Dashboard에서는 이 결과를 카드와 차트 형태로 시각화하고, 내부 Agent 실행 순서 역시 Trace로 확인할 수 있습니다.

---

## 7. Engineering Design

### Tool / Engine / Agent Separation

프로젝트 내부 역할을 세 계층으로 분리했습니다.

**Tools — 데이터와 계산**

```text
market_data.py
indicators.py
ml_predictor.py
regime_tool.py
similarity_tool.py
cycle_tool.py
```

**Engines — 결정 규칙과 점수**

```text
entry_engine.py
exit_engine.py
confidence_gate.py
position_engine.py
```

**Agents — 해석과 최종 의사결정**

```text
technical_agent.py
cycle_agent.py
risk_agent.py
decision_agent.py
critic_agent.py
explanation_agent.py
```

이렇게 분리함으로써 새로운 지표나 Agent를 추가하더라도 전체 실행 코드를 크게 수정하지 않도록 설계했습니다.

---

## 8. From Python Project to Web Service

초기 버전은 Streamlit 기반 단일 애플리케이션이었지만, 최종적으로 **UI와 Agent Core를 완전히 분리**했습니다.

```text
GitHub Pages
React / Vite
      │
      │ HTTPS / JSON
      ▼
Render
FastAPI
      │
      ▼
BTC Agent Orchestrator
      │
      ├─ Upbit Data
      ├─ Rule Engines
      ├─ LightGBM
      ├─ Confidence Gate
      └─ Conditional LLM
```

현재 서비스는:

- React frontend → **GitHub Pages**
- FastAPI backend → **Render / Docker**
- ML model → **LightGBM saved artifact**
- Deployment → **GitHub Actions CI/CD**

구조로 공개 배포되어 있습니다.

로컬 PC가 실행 중이지 않아도 웹에서 Live BTC 분석을 요청할 수 있습니다.

---

## 9. Tech Stack

| Area | Stack |
|---|---|
| Language | Python, JavaScript |
| Data | Pandas, NumPy, Upbit API |
| ML | LightGBM, scikit-learn, joblib |
| Backend | FastAPI, Uvicorn |
| Frontend | React, Vite |
| Agent Architecture | Orchestrator, AgentState, Confidence Gate, Critic Loop |
| Deployment | Docker, Render, GitHub Pages |
| CI/CD | GitHub Actions |

---

## 10. Current Limitations & Next Step

현재 버전은 **가격 / 거래량 / 추세 기반 판단 시스템**에 초점을 두고 있습니다.

다음 버전에서는 시장의 단기 레버리지 구조를 더 잘 판단하기 위해 다음 데이터를 별도 Tool로 연결할 계획입니다.

```text
Open Interest
Funding Rate
Long / Short Ratio
Liquidation Data
ETF Flow
DXY / Treasury Yield
DeFi Borrowing
On-chain Valuation
```

이를 기존 `AgentState`에 `derivatives`, `flow`, `macro`, `onchain` 상태로 추가하고,

```text
Healthy Bull
Leveraged Bull
Short Squeeze
Long Flush
Bearish
Neutral
```

과 같은 단기 Market Regime을 별도로 판별하도록 확장할 예정입니다.

---

## 11. Project Structure

```text
btc-agent/
├── backend/              # FastAPI API layer
├── frontend/             # React dashboard
├── src/
│   ├── core/             # AgentState / Orchestrator
│   ├── tools/            # Data / Indicator / ML / Regime
│   ├── engines/          # Entry / Exit / Gate / Position
│   ├── agents/           # Decision / Risk / Critic / Explanation
│   └── ml/               # Feature / Training / Model Store
├── data/models/          # Saved LightGBM model
├── tests/                # Pipeline / API / ML tests
├── Dockerfile
└── .github/workflows/    # CI/CD
```

---

## Project Summary

> 단일 모델의 판단에 의존하지 않고 설명 가능성과 유연성을 확보하기 위해 BTC 투자 의사결정 보조 Agent를 개발했습니다. Rule로 판단 기준을 명시하고 LightGBM을 보조 신호로 사용했으며, Rule·ML·Regime 간 충돌이나 임계값 근처의 불확실한 Case만 Confidence Gate를 통해 추가 분석하도록 설계했습니다. 이후 FastAPI와 React로 Agent Core와 UI를 분리하고 Docker, Render, GitHub Pages, GitHub Actions를 이용해 실제 웹서비스로 배포했습니다.

---

> **Disclaimer**  
> 이 프로젝트는 투자 판단 구조를 연구하기 위한 개인 프로젝트이며 자동매매 시스템이나 투자 권유 서비스가 아닙니다.
