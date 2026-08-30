import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import HISTORY_YEARS, MARKET
from src.evaluation.backtest import run_score_backtest, summarize_score_backtest
from src.tools.indicators import add_indicators
from src.tools.market_data import get_daily_candles_history


def main():
    print("BTC 데이터 수집...")
    df = get_daily_candles_history(market=MARKET, years=HISTORY_YEARS)
    df = add_indicators(df)

    print("Entry/Exit score backtest...")
    results = run_score_backtest(df)
    summary = summarize_score_backtest(results)

    print("\n===== SUMMARY =====")
    for key, value in summary.items():
        print(f"{key}: {value}")

    output = ROOT / "data" / "processed" / "score_backtest.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output, index=False, encoding="utf-8-sig")
    print("\n저장:", output)


if __name__ == "__main__":
    main()
