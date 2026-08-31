from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.tools.market_data import get_daily_candles_history
from src.validation.v5_walkforward import validate_forecasts_walkforward


def main() -> None:
    parser = argparse.ArgumentParser(description="Run strict walk-forward validation for BitScope V5 forecast distributions.")
    parser.add_argument("--market", default="KRW-BTC")
    parser.add_argument("--years", type=int, default=8)
    parser.add_argument("--points", type=int, default=40, help="Maximum historical as-of points per horizon")
    parser.add_argument("--output", default="validation/v5_walkforward.json")
    args = parser.parse_args()

    raw = get_daily_candles_history(market=args.market, years=args.years)
    result = validate_forecasts_walkforward(raw, max_points_per_horizon=args.points)
    result["market"] = args.market
    result["history_years_requested"] = args.years
    result["dataset"] = "Upbit daily candles fetched at validation runtime"
    result["profitability_claim"] = False
    result["note"] = "Forecast-layer validation only. Full council/risk/portfolio quality must be measured prospectively with the live journal."
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["by_horizon"], ensure_ascii=False, indent=2))
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
