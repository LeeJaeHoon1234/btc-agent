# BTC Agent V4 Architecture

## 1. Multi-speed design

V4 does not pretend that every piece of data is equally real-time.

- **Browser ticker:** Upbit WebSocket; updates with trades.
- **Fast REST snapshot:** ~10 s cache; order book, recent trades, 1m/5m candles, intraday metrics and event detection.
- **Full AI analysis:** ~5 min cache by default; expensive cross-domain research and LLM reasoning.
- **Daily/slow model:** daily features, historical similarity, cycle and 30-day ML probability.

The UI displays these update speeds separately.

## 2. Decision path

```text
RAW FACTS
  │
  ├── Upbit 1m / 5m / ticker / trades / orderbook
  ├── Binance -> Bybit derivatives fallback
  ├── macro
  ├── news
  ├── ETF flow
  ├── sentiment
  ├── Bitcoin network
  └── daily history / saved ML
  │
  ▼
DETERMINISTIC FEATURES
  │
  ├── technical indicators
  ├── microstructure metrics
  ├── returns / volatility / range position
  └── data freshness / missing-data flags
  │
  ▼
EVENT DETECTOR
  │
  ├── fast shock
  ├── flush -> rebound
  ├── high rejection
  ├── volume spike
  └── leverage / funding crowding
  │
  ▼
SIGNAL REGISTRY
  │  facts are assigned IDs; numbers cannot be rewritten by the LLM
  ▼
SPECIALIST RESEARCH
  │
  ▼
HORIZON ANALYST
  ├── NOW
  ├── TODAY
  ├── 1W
  ├── 1M
  └── 1Y
  │
  ▼
CRITIC
  │ checks horizon confusion, unsupported evidence, missing data, ML over-trust
  ▼
PLAIN-LANGUAGE WRITER
  │
  ▼
UI
  ├── Hold
  ├── Add
  ├── Take profit
  ├── plain reasons
  └── recheck conditions
```

## 3. Hardcoded vs autonomous

### Code owns
- exact arithmetic
- indicator definitions
- timestamps
- API success/failure
- source freshness
- model inference
- event *detection* thresholds
- response schema
- LLM quota/cost guard

### AI owns
- which valid signals are most important now
- whether an intraday shock matters more than a slow indicator for NOW
- interpretation of conflicting domains
- different views by horizon
- selecting concise evidence
- plain-language explanation

### AI is not allowed to
- invent a missing number
- alter a supplied market value
- claim unavailable derivatives/on-chain data exists
- treat the weak 30-day ML model as an oracle
- guarantee a return

## 4. Real-time integrity

The main price label says LIVE only when the browser WebSocket is actually connected. If it disconnects, the UI labels the price REST or OFFLINE rather than leaving a misleading LIVE badge.

A fast backend event overlay keeps detecting intraday shocks without running an LLM every few seconds. If a severe event occurs after the last full AI analysis, the UI can show the new event immediately and invite a full AI refresh.
