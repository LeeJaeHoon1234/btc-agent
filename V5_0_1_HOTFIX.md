# BitScope V5.0.1 Hotfix

V5.0.1 is a correctness and presentation hotfix on top of V5.0.0.

## Correctness fixes

- **Technical Council consistency**: an explicit specialist `NEUTRAL` stance now wins over a derived score, preventing a `BULLISH` badge next to a neutral thesis.
- **ETF flow parser**: Farside daily rows now preserve column positions and read the numeric **final Total cell** directly. Missing fund cells (`-`) are no longer dropped before deciding which value is the Total.
- **ETF context**: the latest completed session date and five-session total are included in the evidence text.
- **Unavailable specialist state**: unavailable domains are exposed to the UI as unavailable rather than looking like ordinary neutral confirmation.
- **Council counter-cases**: generic repeated counterarguments are replaced by specialist risks or domain-specific failure conditions.

## Frontend improvements

- Korean UI uses `강세 / 중립 / 약세 / 데이터 부족` instead of raw `BULLISH / NEUTRAL / BEARISH` codes.
- Structural and portfolio regime labels are normalized (`sideways` and `range` both render as `횡보`).
- Acute states such as volatility shocks and liquidation states receive plain Korean labels.
- Risk-cap reasons are translated into plain Korean.
- `Agent Council` / `Risk Governor` engineering jargon is reduced in the Korean main view.

## Documentation

- README updated from the V4.1 architecture description to the actual V5 pipeline:
  `raw facts -> forecast distributions -> independent council -> bounded meta decision -> hard risk governor -> portfolio -> live track record`.
- Validation status explicitly separates engineering correctness from forecasting/profitability claims.

## Validation

- Python regression suite: **32 passed**.
- Frontend `App.jsx`, `i18n.js`, `api.js`, and `main.js`: parsed successfully with the TypeScript JSX/ES parser.
- Full Vite production build could not be completed in the packaging environment because package installation timed out on network access; GitHub Actions remains the production build check.

## External data check that motivated this hotfix

On 2026-08-31, the deployed UI displayed the latest US spot-BTC ETF flow as `+0M`. The latest completed Farside session available at that time was **28 Aug 2026: -201.9M USD**, exposing the parser weakness fixed here.
