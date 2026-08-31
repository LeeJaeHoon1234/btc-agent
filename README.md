# BTC Agent V4.1

BTC Agent V4.1 is a multi-horizon Bitcoin decision-support system built around one principle:

> **Complex inside, simple outside.**

V4.1 keeps the V4 live/multi-horizon engine and improves two areas: **human readability** and **self-evaluation over time**.

## What changed from V4

### 1. Readable live market context

- BTC/KRW remains browser-live through Upbit WebSocket.
- BTC/USD reference price is fetched independently from Coinbase and displayed next to KRW.
- Upbit `signed_change_rate` is explicitly labeled **change vs previous close**, not misleadingly shown as rolling 24h.
- A true rolling 24h return is calculated separately from 60-minute candles.
- “1 hour / 4 hours / from low / from high” are no longer naked numbers: the UI adds plain-language meaning.
- Current price is shown inside the day low-to-high range.
- 1H and 4H cards include sparklines.
- Clicking the chart opens an enlarged 1H / 4H / 1D / 3D view with hover inspection and zoom controls.

### 2. Data sanity layer

The fast layer now checks:

- positive/valid prices
- high >= low
- current price inside the reported day range
- consistency of the computed range position
- ticker vs latest 1-minute candle divergence
- KRW and USD reference-price cross-check

If values are inconsistent, the UI shows a warning instead of silently presenting the number as trustworthy.

### 3. Prediction Journal + Reflection Memory

V4.1 records the five horizon decisions and later evaluates them after their horizon matures:

| Horizon | Evaluation delay |
|---|---:|
| NOW | 4 hours |
| TODAY | 24 hours |
| 1W | 7 days |
| 1M | 30 days |
| 1Y | 365 days |

Each journal item stores the original stance, confidence, entry price, regime and selected evidence IDs/domains. When the horizon matures, the system compares the original view with the realized price move and produces a structured lesson.

When an LLM budget slot is available, a Reflect Agent may refine the lesson into `attention_up` / `attention_down` guidance. It is **not allowed** to change indicator thresholds, model weights or realized returns. If the LLM call is unavailable, the deterministic reflection remains valid.

### 4. Memory is a weak prior, not an auto-trading optimizer

Reflection memory is passed to the V4.1 Horizon Analyst with strict rules:

- current market data always outranks memory
- fewer than 3 historical samples are treated as insufficient evidence
- no automatic RSI/score/position threshold mutation
- performance by regime/domain is context, not a direct trading weight

### 5. More independent specialists

Technical / derivatives / macro / news / historical specialists still inspect their own domains. The V4.1 Horizon Analyst receives their **summary/evidence/risks**, but not their final numeric score as an anchor. The old cross-domain research synthesis is retained for Advanced/backward compatibility and is deterministic in the V4.1 path, saving one LLM call.

## Main architecture

```text
Live market / derivatives / macro / news / flow / on-chain
                         │
                         ▼
              deterministic calculations
                         │
                         ▼
                data sanity checks
                         │
                         ▼
                  signal registry
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
 independent specialists        reflection memory
          └──────────────┬──────────────┘
                         ▼
                 Horizon Analyst
              NOW / TODAY / 1W / 1M / 1Y
                         │
                         ▼
                       Critic
                         │
                         ▼
               Plain-language Writer
                         │
                         ▼
                    React UI
                         │
                     time passes
                         │
                         ▼
                realized outcome
                         │
                         ▼
               Reflection Engine
                         │
                         └──────► next analysis context
```

## LLM budget

The existing `MAX_LLM_CALLS_PER_ANALYSIS=8` remains enough. A normal full run is typically:

1. derivatives specialist
2. macro specialist
3. news specialist
4. historical specialist
5. horizon analyst
6. critic
7. plain-language writer
8. optional Reflect Agent **only when matured predictions exist**

The old cross-domain synthesis is deterministic in V4.1. If quota/budget is unavailable, specialist/horizon/writer/reflection modules all have deterministic fallbacks.

## API

- `GET /health` — V4.1 capability state
- `GET /api/v1/live` — cheap fast-layer snapshot, no LLM
- `POST /api/v1/analyze` — full five-horizon analysis
- `GET /api/v1/journal` — recent prediction/reflection history
- `GET /api/v1/usage` — anonymous process-local quota counters

## Persistence note

The default prediction journal is a local JSON file under `data/runtime/`. On ephemeral hosting such as a default Render filesystem, that memory can disappear on restart/redeploy. For durable long-term learning, point `PREDICTION_JOURNAL_PATH` at a persistent disk or migrate the journal store to a database.

## Verification

Backend:

```bash
python -m pytest -q
```

Expected for V4.1:

```text
23 passed
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

The generated package was syntax-checked with the TypeScript JSX parser. The build environment used here could not reach the npm registry, so the production Vite build must run locally or in GitHub Actions.

## Disclaimer

This is a research/decision-support project, not an automated trading system or a promise of returns.
