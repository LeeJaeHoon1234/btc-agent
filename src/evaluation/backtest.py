import pandas as pd

from src.agents.technical_agent import run_technical_agent
from src.engines.entry_engine import score_entry
from src.engines.exit_engine import score_exit
from src.tools.cycle_tool import analyze_cycle
from src.tools.regime_tool import detect_regime


def run_score_backtest(
    df: pd.DataFrame,
    forward_days: int = 30,
    min_history: int = 400,
) -> pd.DataFrame:
    """
    LLM 없이 deterministic score만 과거에 재생한다.
    현재 v2의 첫 백테스트는 Entry/Exit score가 미래 수익률과 어떤 관계인지 확인하는 용도다.
    """
    rows: list[dict] = []

    for i in range(min_history, len(df) - forward_days):
        historical = df.iloc[: i + 1]
        latest = historical.iloc[-1]

        technical = run_technical_agent(historical)
        regime = detect_regime(historical)
        cycle = analyze_cycle(historical)

        # 백테스트 속도를 위해 ML/Similarity는 중립 처리
        ml = {"available": False}
        similarity = {"available": False}

        entry = score_entry(technical, ml, regime, similarity)

        latest_dict = {
            "rsi14": latest["rsi14"],
            "ma200_gap_pct": latest["ma200_gap_pct"],
            "ma350_gap_pct": latest["ma350_gap_pct"],
            "return_90d": latest["return_90d"],
            "return_365d": latest["return_365d"],
            "drawdown_30d_pct": latest["drawdown_30d_pct"],
            "ma20_slope_5d": latest["ma20_slope_5d"],
            "return_7d": latest["return_7d"],
            "volume_ratio": latest["volume_ratio"],
        }
        exit_signal = score_exit(latest_dict, cycle)

        current_price = float(latest["close"])
        future_price = float(df.iloc[i + forward_days]["close"])
        future_return = (future_price / current_price - 1) * 100

        rows.append(
            {
                "date": latest["date"],
                "close": current_price,
                "entry_score": entry["score"],
                "exit_score": exit_signal["score"],
                "regime": regime["regime"],
                "cycle_stage": cycle["stage"],
                f"forward_return_{forward_days}d": future_return,
            }
        )

    return pd.DataFrame(rows)


def summarize_score_backtest(results: pd.DataFrame, forward_days: int = 30) -> dict:
    target = f"forward_return_{forward_days}d"

    high_entry = results[results["entry_score"] >= 70]
    high_exit = results[results["exit_score"] >= 75]

    return {
        "rows": int(len(results)),
        "high_entry_count": int(len(high_entry)),
        "high_entry_avg_forward_return": (
            None if high_entry.empty else float(high_entry[target].mean())
        ),
        "high_entry_up_rate": (
            None if high_entry.empty else float((high_entry[target] > 0).mean() * 100)
        ),
        "high_exit_count": int(len(high_exit)),
        "high_exit_avg_forward_return": (
            None if high_exit.empty else float(high_exit[target].mean())
        ),
        "high_exit_down_rate": (
            None if high_exit.empty else float((high_exit[target] < 0).mean() * 100)
        ),
    }
