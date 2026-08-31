# BTC Agent V4

BTC Agent V4 is a multi-horizon Bitcoin decision-support system designed around one principle:

> **Complex inside, simple outside.**

The backend can inspect many market, derivatives, macro, flow, sentiment, network and model signals, while the main UI answers only the questions a user actually needs:

- What is happening **right now**?
- What does **today** look like?
- What is the view for **1 week / 1 month / 1 year**?
- For an existing position, should I **hold, add, or consider taking profit**?
- What would make the view change?

This is a research/decision-support project, not an automated trading system or a promise of returns.

## What changed from V3.1

V3.1 exposed too much of the internal agent architecture on the main screen and its primary market model was daily-data oriented. V4 separates the system into different speeds and hides implementation detail from the default UI.

### Real-time / fast layer

- Browser-side Upbit WebSocket ticker for a genuinely moving BTC/KRW price.
- Backend `/api/v1/live` snapshot cached for ~10 seconds.
- Upbit 1-minute + 5-minute candles.
- Recent trades and aggressive buy/sell balance.
- Order-book imbalance and spread.
- 5m / 15m / 1h / 4h / 24h price movement.
- Rebound from the 24h low and distance from the 24h high.
- VWAP gap, RSI, EMA, MACD, Bollinger position, ATR, realized volatility and volume anomaly metrics.
- Event detector for fast shocks, flush/rebound, high rejection, volume spikes and leverage events.

### Slow / structural layer

The existing daily core remains available and was expanded with:

- MA20 / 50 / 60 / 100 / 111 / 200 / 350
- EMA9 / 12 / 21 / 26 / 50 / 200
- RSI14
- MACD
- Bollinger Bands
- ATR
- ADX / DI
- Stochastic
- OBV
- volume ratio / volume z-score
- multi-period returns
- multi-period volatility
- drawdowns
- cycle proxies
- existing 30-day LightGBM model as a **supporting** signal only
- historical similarity retrieval

## Multi-horizon analysis

V4 analyzes five horizons independently:

| Horizon | Main question |
|---|---|
| NOW | What is happening in the market right now? |
| TODAY | What kind of intraday session is this? |
| 1W | What is the short-term direction? |
| 1M | What does the medium-term setup look like? |
| 1Y | Where are we in the broader structure/cycle? |

The same indicator is not forced to mean the same thing at every horizon. For example, an overbought 1-minute RSI during a sharp rebound is not automatically interpreted as a one-month market top.

## External evidence

V4 is best-effort and never converts missing data into fake neutral evidence.

- **Derivatives:** Binance USD-M Futures primary; Bybit Linear fallback for funding/open interest and available positioning data.
- **Macro:** FRED when configured, with the existing public fallback.
- **News:** recent Bitcoin-focused retrieval through Google News RSS.
- **US spot-BTC ETF flow:** public Farside snapshot (best-effort parser; marked unavailable if page structure changes).
- **Sentiment:** Alternative.me Fear & Greed.
- **Bitcoin network:** Blockchain.com stats + mempool.space fee data.
- **Valuation on-chain metrics:** MVRV/SOPR/LTH-STH metrics are explicitly marked missing unless a real provider is added. V4 does not fabricate them.

## AI autonomy: bounded, not fake autonomy

V4 deliberately separates facts from interpretation.

```text
Upbit / derivatives / macro / news / flow / network
                         │
                         ▼
              deterministic calculations
                         │
                         ▼
                   signal registry
              (facts + source + horizon)
                         │
                         ▼
       specialist LLMs + cross-domain synthesis
                         │
                         ▼
             V4 Horizon Analyst (LLM)
             NOW / TODAY / 1W / 1M / 1Y
                         │
                         ▼
                 independent Critic
                         │
                         ▼
              Plain-language Writer
                         │
                         ▼
                   React dashboard
```

Python owns exact numbers, timestamps, API status and indicator calculations. The V4 Horizon Analyst is allowed to decide **which evidence matters most**, reconcile conflicting signals and produce different conclusions by horizon. It may only cite IDs from the supplied signal registry; it cannot invent market values.

The default LLM budget remains at most 8 calls per full analysis. With specialist LLMs enabled, the normal upper bound is:

1. derivatives specialist
2. macro specialist
3. news specialist
4. historical specialist
5. cross-domain synthesis
6. V4 horizon analyst
7. independent critic
8. plain-language writer

If the LLM quota is unavailable, the entire pipeline still returns deterministic fallback horizons and a usable UI.

## Frontend philosophy

The main page no longer exposes Planner, research delta, entry score, expert score and evidence logs as the primary experience.

The default page shows:

1. genuinely live price and update age
2. current market event
3. simple hold / add / take-profit actions
4. NOW / TODAY / 1W / 1M / 1Y tabs
5. a few plain-language reasons
6. what to watch next
7. data-source freshness/status

Raw metrics, old core scores, model metadata, research results, critic output and execution trace live under **Detailed analysis**.

## API

### `GET /health`
Service health and V4 capabilities.

### `GET /api/v1/live?market=KRW-BTC`
Cheap fast-layer snapshot. No LLM call. Intended for frequent polling/fallback when the browser WebSocket is unavailable.

### `POST /api/v1/analyze`
Full multi-horizon analysis.

Example request:

```json
{
  "market": "KRW-BTC",
  "history_years": 8,
  "source": "live",
  "question": "현재 BTC를 NOW, TODAY, 1W, 1M, 1Y 관점에서 분석하고 보유·추가매수·익절 대응을 판단해줘."
}
```

### `GET /api/v1/usage`
Anonymous process-local request/LLM quota counters.

## Project structure

```text
backend/                 FastAPI API + fast/full caches
frontend/                React/Vite dashboard
src/
  agents/v3/             retained specialist research layer
  agents/v4/             horizon autonomy, critic, user writer
  core/                   AgentState + V4 orchestrator
  engines/v4/            signal registry + horizon fallback engine
  tools/                  daily + intraday calculations
  tools/research/         derivatives/macro/news/ETF/sentiment/network
data/models/              existing saved LightGBM artifacts
tests/                    API/core/V3 compatibility/V4 tests
```

## Local verification

Backend:

```bash
python -m pytest -q
```

Expected for this V4 package:

```text
20 passed
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

Then run the backend and frontend with the existing helper scripts or your normal commands.

## Deployment

The existing deployment topology is preserved:

```text
GitHub Pages (React)
        │
        ▼
Render (FastAPI / Docker)
        │
        ├─ Upbit
        ├─ derivatives providers
        ├─ macro/news/flow/network sources
        └─ OpenAI API (server-side key only)
```

Keep `OPENAI_API_KEY` only in Render. Do not commit it.

If your existing repository already contains `data/models/btc_lgbm.joblib` and `btc_lgbm_metadata.json`, **keep those files** when overlaying the V4 update. The provided source package does not recreate a model that was not present in the supplied V3 archive.

See `V4_ROLLOUT.md` for the exact upgrade steps.
