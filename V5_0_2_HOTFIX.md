# BitScope V5.0.2 Hotfix

V5.0.2 is an end-to-end correctness and Agent Council readability hotfix on top of V5.0.1.

## Why this release exists

The live UI exposed two integration bugs that unit-level logic alone did not catch:

1. The V5.0.1 council correctly preferred an explicit specialist stance, but the orchestrator removed `stance` and `raw_score` before the council received the specialist view. A technical specialist could therefore say `NEUTRAL 63/100` while the council badge re-derived `BULLISH` from the normalized score.
2. Farside can expose the current US ETF session before it is complete. An in-progress `0.0M` row could become the latest session and also contaminate the rolling five-session sum.

## Fixes

- Preserve specialist `stance`, `raw_score`, `raw`, evidence and confidence across the orchestrator → council boundary.
- Treat the current New York ETF-flow date as **provisional**, never as completed decision evidence.
- Keep provisional ETF values separately while using the most recent completed session for `latest_total_musd` and the five-session sum.
- Balance latest-session and rolling five-session ETF flow only in the deterministic fallback prior; raw values stay untouched for autonomous analysis.
- Split the previous `Macro & News` council card into independent `Macro` and `News & Events` members.
- Make unavailable council members display `데이터 부족` without a misleading confidence percentage.
- Show the risk member as `리스크 압력 N/100` instead of `NEUTRAL xx%`.
- Show whether a council card came from an independent specialist or a deterministic fallback.
- Expand the council UI from three compressed columns to two readable columns on desktop.
- Expand the technical thesis with the specialist's actual score and top technical evidence.
- Rename the flow card to `ETF·네트워크` until full on-chain valuation metrics are connected.

## Verification

- Python regression suite: `36 passed`
- Frontend source parse: `App.jsx`, `i18n.js`, `api.js`, `main.js` pass TypeScript JSX/JS parsing.
- Live source cross-check: Farside's latest completed 2026-08-28 session is `-201.9M USD`; completed 5-session total through that date is `+924.5M USD`.

This release does not retrain or change the LightGBM model.
