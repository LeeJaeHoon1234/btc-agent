# BTC Agent V4.1 Architecture

## Fast UI path

```text
Upbit WebSocket -> live KRW price
Upbit REST      -> day high/low, 1m/5m/60m candles, trades, orderbook
Coinbase        -> BTC/USD reference
                     │
                     ▼
              sanity validation
                     │
                     ▼
        plain live-context interpretation
                     │
                     ▼
React Hero + sparklines + range + expandable chart
```

## Full analysis path

```text
Daily core + Fast layer + External evidence
                     │
                     ▼
              Signal Registry
                     │
          Independent Specialists
                     │
        Reflection Memory (weak prior)
                     │
                     ▼
              Horizon Analyst
          NOW TODAY 1W 1M 1Y
                     │
                     ▼
                   Critic
                     │
                     ▼
          Plain-language Writer
```

## Learning path

```text
Horizon decision
   -> Prediction Journal
   -> wait until horizon matures
   -> realized return
   -> structured grade
   -> optional LLM Reflect refinement
   -> lesson + regime/domain performance matrix
   -> weak context in a future Horizon Analyst call
```

Hard numerical thresholds are never auto-modified by reflection memory.
