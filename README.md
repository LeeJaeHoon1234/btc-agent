# BTC Agent V3 — Autonomous Research & Decision System

> **Planner × Specialist Skills × External Tools × Retrieval/RAG × Rule/ML × Confidence Gate × Critic**

A BTC decision-support system that does more than run a fixed indicator pipeline. V3 receives a research question, decides which specialist skills are needed, gathers external evidence, retrieves relevant historical/news context, synthesizes the findings, and then combines them with a bounded Rule/ML decision engine.

**Live service:** `https://LeeJaeHoon1234.github.io/btc-agent/`

---

## Why I Built It

A single model is not enough for investment decisions.

- **Rules** are explicit and interpretable, but depend on manually chosen thresholds.
- **ML** can learn non-linear patterns, but its probability is unreliable when validation performance is weak or the market regime changes.
- **LLMs** are good at research synthesis and resolving conflicting evidence, but should not be allowed to invent market facts or directly override deterministic signals.
- **Real decisions require research**: derivatives positioning, macro conditions, recent catalysts, and historical analogs often matter as much as RSI or moving averages.

V3 therefore separates **fact collection, deterministic calculation, retrieval, specialist interpretation, routing, synthesis, criticism, and final decision**.

---

## V3 Architecture

```text
User Research Question
        │
        ▼
┌──────────────────────────┐
│      Planner Agent       │
│ selects required skills  │
└────────────┬─────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────┐
│              Specialist Research Layer              │
│                                                     │
│ Technical   Derivatives   Macro   News/RAG   History│
│    │            │          │        │          │     │
│    └────────────┴──────────┴────────┴──────────┘     │
│                         │                           │
│                 Evidence Registry                  │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
                 Research Synthesizer
                          │
                          ▼
                 Bounded Research Engine
                 (max ±8 score impact)
                          │
       ┌──────────────────┴──────────────────┐
       │                                     │
       ▼                                     ▼
Rule / Technical Engine                LightGBM Model
       │                                     │
       └──────────────────┬──────────────────┘
                          ▼
                   Confidence Gate
                          │
                  Fast / Deep Route
                          │
                 Risk + Decision Agent
                          │
                      Critic Loop
                          │
                    Position Engine
                          │
                  Explanation Agent
                          │
                          ▼
                    React Web UI
```

---

## Skill-Based Agent Design

Each specialist is defined by an explicit `SKILL.md` rather than only a Python filename.

```text
skills/
├── technical/SKILL.md
├── derivatives/SKILL.md
├── macro/SKILL.md
├── news/SKILL.md
├── historical/SKILL.md
└── risk/SKILL.md
```

A skill describes the specialist's mission, available tools, analysis procedure, guardrails, and expected output. The `SkillRegistry` loads these files at runtime, and the Planner can route a question to only the skills that are needed.

When LLM access is disabled, the same orchestration continues with deterministic fallbacks. When LLM access is enabled, the skill instructions become the specialist system context. `USE_SPECIALIST_LLM` can disable per-specialist LLM calls while keeping Planner/Synthesis reasoning available.

---

## Autonomous Planner

The system no longer runs every research module blindly.

Examples:

```text
"Is this rally a short squeeze?"
→ Technical + Derivatives + Risk

"Why is BTC rising despite a stronger dollar?"
→ Technical + Derivatives + Macro + News + Risk

"Does this look like a cycle top?"
→ Technical + Historical Retrieval + Macro + Derivatives + Risk
```

With LLM enabled, the Planner chooses the route from the available skill catalog. Without LLM, a deterministic intent router provides a safe fallback.

---

## Specialist Agents

### 1. Technical Analyst

Uses the original deterministic feature layer:

- RSI14
- MA20 / MA200 gaps and slopes
- volume ratio
- 3D / 7D / 30D returns
- volatility and drawdown

This remains the stable core of the system.

### 2. Derivatives Analyst

Uses public Binance USD-M Futures market-data endpoints to examine:

- funding rate
- current open interest
- 24h open-interest change
- global long/short ratio
- top-trader position ratio
- taker buy/sell ratio

It classifies the derivatives regime into states such as:

```text
HEALTHY_BULL
LEVERAGED_BULL
SHORT_SQUEEZE
LONG_FLUSH
BEARISH_LEVERAGE
NEUTRAL
```

### 3. Macro Analyst

Evaluates whether the dollar and U.S. Treasury yield backdrop is helping or hurting BTC.

Primary optional source:

- FRED API (`FRED_API_KEY`)

Fallback:

- public market-chart data for the dollar index and U.S. 10Y yield

Unavailable data is explicitly marked as unavailable rather than silently treated as neutral.

### 4. News Research + RAG Agent

Searches recent public BTC news, deduplicates the results, and retrieves only items relevant to the current research question using TF-IDF retrieval.

The agent preserves:

- headline
- source
- publication time
- URL
- retrieval score

The final UI exposes these records through the **Evidence Registry** instead of presenting uncited LLM claims.

### 5. Historical RAG Agent

The original similarity logic is extended into a historical retrieval layer.

Current BTC state is matched against past states using standardized features such as:

- momentum
- moving-average structure
- volume
- volatility
- drawdown

For each retrieved case, the system records forward 7D and 30D returns. The aggregate uses the median and dispersion rather than cherry-picking a single historical example.

---

## Evidence Registry

One of the main V3 changes is that specialist conclusions are no longer just strings passed between agents.

Each research item can be stored as structured evidence:

```json
{
  "id": "E7",
  "agent": "news",
  "kind": "source",
  "title": "...",
  "claim": "...",
  "url": "...",
  "source": "...",
  "confidence": 0.68
}
```

This gives the final Decision/Critic layer a traceable record of where a claim came from.

---

## Research Cannot Overwrite the Core Engine

A major design constraint is that external research and LLM reasoning are **bounded**.

The cross-domain research score can move the original Entry score by at most:

```text
±8 points
```

This prevents one noisy headline, failed API, or hallucinated LLM interpretation from completely overriding the Rule/ML engine.

```text
Core Entry Score
      +
Bounded Research Adjustment
      ↓
Adjusted Entry Score
```

If core signals and research strongly disagree, the Confidence Gate automatically routes the case to deeper review.

---

## Rule + ML Core

The original V2 engine is preserved as the deterministic base.

### Entry Engine

Combines:

- technical condition
- LightGBM 30D probability
- market regime
- historical similarity

### Exit Engine

Separately evaluates long-term overheating and cycle-top risk.

### LightGBM

Training is separated from runtime.

```text
Historical BTC Data
        ↓
Feature Engineering
        ↓
Walk-Forward Validation
        ↓
Final Model
        ↓
btc_lgbm.joblib
```

The web service loads the saved model instead of retraining on every request.

---

## Confidence Gate & Critic Loop

The system uses conditional routing instead of asking an LLM to decide everything.

```text
Low conflict
→ Fast Path

Signal conflict / weak confidence / research disagreement
→ Deep Analysis
→ Decision Agent
→ Critic Agent
→ Revision
```

The Critic explicitly checks:

- Entry vs Exit conflict
- weak ML validation being over-interpreted
- regime vs action conflict
- missing top-risk signals
- disagreement between core and autonomous research
- missing invalidation conditions

---

## Web Service Architecture

```text
GitHub Pages
React / Vite
     │
     │ HTTPS JSON
     ▼
Render
FastAPI / Docker
     │
     ├── Upbit market data
     ├── Binance derivatives data
     ├── Macro data provider
     ├── News search / retrieval
     ├── Historical RAG
     ├── LightGBM
     └── Optional LLM agents
```

The browser never receives private API keys. LLM and macro API credentials are server-side environment variables only.

---

## Failure-Tolerant Design

External research is intentionally non-critical.

- Binance unavailable → derivatives specialist returns `UNAVAILABLE`
- Macro source unavailable → macro evidence is marked missing
- News search unavailable → core decision engine still runs
- LLM unavailable → deterministic Planner and specialist fallbacks run
- ML model unavailable → ML returns a neutral fallback instead of crashing the service

The deterministic BTC engine remains usable even when the autonomous research layer is partially degraded.

---

## Current Scope and Limitations

V3 is still a **decision-support research system**, not an automated trading bot.

Current limitations include:

- no exchange order execution
- no liquidation heatmap provider yet
- no proprietary exchange-flow / whale-flow on-chain provider
- headline-level public news retrieval rather than full paid news feeds
- LightGBM performance must be interpreted through walk-forward validation
- historical analogs are descriptive, not causal forecasts

---

## Next Research Directions

Planned extensions:

```text
On-chain / DeFi Specialist
├── exchange inflow / outflow
├── stablecoin liquidity
├── MVRV / SOPR
└── DeFi borrowing utilization

Liquidation Specialist
├── liquidation clusters
├── leverage concentration
└── squeeze-risk estimation

Agent Memory
├── previous decisions
├── what invalidated them
└── post-decision evaluation

Automated Evaluation
├── decision log
├── future-return outcome
├── calibration
└── agent-level attribution
```

The long-term objective is not to maximize the number of agents. It is to build a system where each agent owns a clearly defined source of evidence, and the final decision remains traceable and testable.

---

## Project Summary

**BTC Agent V3** evolved from a fixed Rule + LightGBM + conditional-LLM pipeline into an autonomous research architecture.

The main engineering contribution is the separation of:

```text
Data / Tools
→ Retrieval
→ Skills
→ Specialist Agents
→ Planner
→ Research Synthesis
→ Bounded Decision Engine
→ Confidence Gate
→ Critic
→ Final Position Decision
```

The system is designed so that AI adds research and reasoning capability without replacing deterministic validation, evidence traceability, or risk controls.
