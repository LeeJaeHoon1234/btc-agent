import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values("date").reset_index(drop=True)

    # 이동평균
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma60"] = df["close"].rolling(60).mean()
    df["ma111"] = df["close"].rolling(111).mean()
    df["ma200"] = df["close"].rolling(200).mean()
    df["ma350"] = df["close"].rolling(350).mean()

    # 이동평균 기울기
    df["ma20_slope_5d"] = (df["ma20"] / df["ma20"].shift(5) - 1) * 100
    df["ma200_slope_20d"] = (df["ma200"] / df["ma200"].shift(20) - 1) * 100

    # RSI 14 - 기존 프로젝트 방식 유지
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi14"] = 100 - (100 / (1 + rs))
    df.loc[(avg_loss == 0) & (avg_gain > 0), "rsi14"] = 100

    # 거래량
    df["volume_ma20"] = df["volume"].rolling(20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma20"]

    # 현재 시점 모멘텀
    for days in [3, 7, 30, 90, 365]:
        df[f"return_{days}d"] = (df["close"] / df["close"].shift(days) - 1) * 100

    # 이동평균 이격
    df["ma20_gap_pct"] = (df["close"] / df["ma20"] - 1) * 100
    df["ma200_gap_pct"] = (df["close"] / df["ma200"] - 1) * 100
    df["ma350_gap_pct"] = (df["close"] / df["ma350"] - 1) * 100

    # Pi Cycle proxy: 111DMA / (2 * 350DMA)
    df["pi_cycle_ratio"] = df["ma111"] / (2 * df["ma350"])
    df["pi_cycle_distance_pct"] = (1 - df["pi_cycle_ratio"]) * 100

    # 고점 대비 낙폭
    df["ath_to_date"] = df["close"].cummax()
    df["drawdown_from_ath_pct"] = (df["close"] / df["ath_to_date"] - 1) * 100

    df["rolling_high_30d"] = df["close"].rolling(30).max()
    df["drawdown_30d_pct"] = (df["close"] / df["rolling_high_30d"] - 1) * 100

    # 변동성: 일간 수익률 30일 표준편차를 연율화
    daily_return = df["close"].pct_change()
    df["volatility_30d_pct"] = daily_return.rolling(30).std() * np.sqrt(365) * 100

    return df
