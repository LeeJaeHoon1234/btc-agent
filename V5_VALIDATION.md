# BitScope V5 Validation Notes

## What is validated automatically

`python -m pytest -q` currently covers the legacy pipeline plus V5-specific invariants.

V5 regression tests verify that:

1. raw facts do not leak `direction` or `strength`;
2. an independent specialist cannot be overwritten by deterministic priors;
3. the Risk Governor never raises proposed exposure;
4. upside and downside volatility shocks are handled asymmetrically;
5. portfolio changes obey the governor's single-change limit;
6. all five forecast horizons return bounded probabilities and ordered quantiles;
7. long-horizon confidence is capped;
8. strict walk-forward validation returns bounded calibration metrics.

Current test target:

```text
30 passed
```

## Strict walk-forward validation

Run:

```bash
python scripts/validate_v5.py --market KRW-BTC --years 8 --points 40
```

At every historical evaluation timestamp, the validator truncates the dataframe to that timestamp before generating a forecast. Realized returns are read only afterward from the untouched dataset. This prevents future rows from leaking into the forecast.

Metrics include:

- direction accuracy
- Brier score
- expected-return MAE
- q10–q90 coverage
- average forecast confidence

## Engineering sanity result in the build environment

The build environment could not access Upbit DNS, so a 1,900-day synthetic dataset was used only to test the validator itself. The result is stored at `validation/v5_demo_walkforward.json`.

The synthetic result did **not** show a reliable predictive edge. In particular, the 1-year empirical interval was under-covered. This is intentionally treated as a warning, not tuned away against synthetic data.

Therefore V5 does **not** claim profitability. Numerical distributions are explicitly marked as requiring walk-forward/live calibration.

## What still requires real evidence

The full V5 allocation combines real-time derivatives, macro, news, flows and market microstructure. Those historical snapshots are not reconstructed by the daily-price validator. The complete system therefore needs a **prospective live track record**.

The Prediction Journal is the authoritative path for that evidence: save the decision when it happened, wait for the horizon to mature, then score the frozen prediction. Do not recreate old predictions with today's model and call that a live track record.
