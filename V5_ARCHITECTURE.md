# BitScope V5 Architecture

## Goal

V5 changes BitScope from a signal dashboard into an auditable Bitcoin decision-intelligence system. The core design rule is:

> **Raw facts stay raw. Numerical models own numbers. LLMs interpret and challenge. A deterministic Risk Governor owns the safety boundary.**

## Main pipeline

```text
Live + daily + external data
        ↓
Data health / sanity checks
        ↓
Signal Registry (backward compatibility)
        ↓
Fact / Prior Split
 ├─ Raw Facts ───────────────────────────────┐
 └─ Deterministic Priors (fallback only)     │
                                              ↓
Historical-neighbor Forecast Distributions   Agent Council
NOW / TODAY / 1W / 1M / 1Y                  ├─ Technical
                                              ├─ Derivatives
Two-speed Market State                        ├─ On-chain / Flow
structural regime + acute state               ├─ Macro / News
                                              ├─ Historical
                                              └─ Risk
                    ↓                         ↓
                  Quantitative Base Decision
                              ↓
                   Bounded Meta Decision Agent
                (LLM may adjust only ±10%p)
                              ↓
                     Hard Risk Governor
             (can cap/block, can never increase)
                              ↓
                       Portfolio Engine
        target exposure / step-limited change / anchors
                              ↓
             Horizon Analyst + Critic + Plain Writer
                              ↓
                  Prediction Journal / Track Record
                              ↓
             realized outcome + calibration metrics
```

## Why facts and priors are separated

V4.1 attached `direction` and `strength` to evidence before the LLM saw it. That was useful for deterministic fallback, but it could anchor an autonomous analyst on hand-written thresholds.

V5 therefore exposes two objects:

- `facts`: value, domain, horizon, freshness and plain factual text only.
- `deterministic_priors`: direction/strength used only when an independent specialist is unavailable.

The V5 Horizon Analyst receives `facts`, not the directional priors.

## Forecast layer

The numerical forecast layer produces a distribution instead of a single direction label:

- expected return
- median return
- q10 / q25 / q75 / q90
- probability of finishing higher
- > +5% and < -5% tail probabilities
- dispersion
- effective sample size
- analog distance
- confidence
- calibration status

`NOW` uses a damped intraday state distribution. `TODAY`, `1W`, `1M`, and `1Y` use distance-weighted historical neighbors with strict exclusion of recent rows.

Directional probabilities are shrunk toward 50% based on effective sample size and horizon so small analog sets do not appear as false 0%/100% certainty. Long-horizon confidence is capped more aggressively.

## Agent Council

Council members do not vote directly on position size. Each domain provides:

- stance
- confidence
- thesis
- counterargument
- cited raw fact IDs
- source (`independent_specialist` or deterministic fallback)

If an independent specialist exists, its own domain regime/score takes precedence. Deterministic priors cannot overwrite it.

## Decision authority

### Quantitative Base Decision
Combines forecast utilities, council imbalance, risk pressure and acute market state.

### Meta Decision Agent
The LLM may challenge the quantitative target, but only inside an auditable ±10 percentage-point band. It cannot invent portfolio math.

### Risk Governor
A non-LLM safety layer. It can only lower or block proposed exposure. It checks:

- critical data availability
- missing-source count
- forecast downside tails
- negative volatility shocks / leverage states
- adverse event severity and direction
- high agent disagreement

An upside volatility shock does **not** automatically trigger a risk cap.

### Portfolio Engine
Converts approved target exposure into a step-limited change from the user's current exposure. It also publishes scenario anchors for entry, weakness, invalidation and upside; these are not orders.

## Track Record

Live decisions store the forecast distribution and model version at decision time. When a horizon matures, the journal evaluates:

- realized return
- directional alignment
- Brier score
- absolute expected-return error
- q10–q90 interval coverage

Historical memory is a weak prior only. It cannot silently rewrite model parameters or market facts.
