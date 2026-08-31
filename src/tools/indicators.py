import numpy as np
import pandas as pd


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs)); out.loc[(avg_loss == 0) & (avg_gain > 0)] = 100
    return out


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Daily feature store.

    V4 deliberately computes a broad technical set here, while the decision layer chooses
    which indicators are relevant for each horizon. Existing ML feature columns are unchanged.
    """
    df = df.copy().sort_values("date").reset_index(drop=True)
    close = df["close"].astype(float); high = df["high"].astype(float); low = df["low"].astype(float); volume = df["volume"].astype(float)

    for window in [20, 50, 60, 111, 100, 200, 350]:
        df[f"ma{window}"] = close.rolling(window).mean()
    for span in [9, 12, 21, 26, 50, 200]:
        df[f"ema{span}"] = close.ewm(span=span, adjust=False).mean()

    df["ma20_slope_5d"] = (df["ma20"] / df["ma20"].shift(5) - 1) * 100
    df["ma50_slope_10d"] = (df["ma50"] / df["ma50"].shift(10) - 1) * 100
    df["ma200_slope_20d"] = (df["ma200"] / df["ma200"].shift(20) - 1) * 100
    df["rsi14"] = _rsi(close, 14)

    # MACD
    df["macd"] = df["ema12"] - df["ema26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # Bollinger Bands
    df["bb_mid"] = df["ma20"]
    bb_std = close.rolling(20).std(ddof=0)
    df["bb_upper"] = df["bb_mid"] + 2 * bb_std
    df["bb_lower"] = df["bb_mid"] - 2 * bb_std
    df["bb_width_pct"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"] * 100
    df["bb_position"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

    # ATR / ADX
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    df["atr14"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    df["atr14_pct"] = df["atr14"] / close * 100
    up_move = high.diff(); down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr = df["atr14"].replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df["adx14"] = dx.ewm(alpha=1 / 14, adjust=False).mean()
    df["plus_di14"] = plus_di; df["minus_di14"] = minus_di

    # Stochastic oscillator
    low14 = low.rolling(14).min(); high14 = high.rolling(14).max()
    df["stoch_k"] = (close - low14) / (high14 - low14).replace(0, np.nan) * 100
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # Volume / OBV
    df["volume_ma20"] = volume.rolling(20).mean()
    df["volume_ratio"] = volume / df["volume_ma20"]
    df["volume_zscore_30d"] = (volume - volume.rolling(30).mean()) / volume.rolling(30).std(ddof=0).replace(0, np.nan)
    direction = np.sign(close.diff()).fillna(0)
    df["obv"] = (direction * volume).cumsum()
    df["obv_slope_10d"] = (df["obv"] - df["obv"].shift(10)) / volume.rolling(20).mean().replace(0, np.nan)

    # Momentum
    for days in [1, 3, 7, 14, 30, 90, 180, 365]:
        df[f"return_{days}d"] = (close / close.shift(days) - 1) * 100
    df["roc14"] = (close / close.shift(14) - 1) * 100

    for window in [20, 50, 200, 350]:
        df[f"ma{window}_gap_pct"] = (close / df[f"ma{window}"] - 1) * 100
    # Backward-compatible names expected by V2/V3 and saved ML feature schema.
    df["ma20_gap_pct"] = df["ma20_gap_pct"]
    df["ma200_gap_pct"] = df["ma200_gap_pct"]
    df["ma350_gap_pct"] = df["ma350_gap_pct"]

    df["pi_cycle_ratio"] = df["ma111"] / (2 * df["ma350"])
    df["pi_cycle_distance_pct"] = (1 - df["pi_cycle_ratio"]) * 100
    df["ath_to_date"] = close.cummax()
    df["drawdown_from_ath_pct"] = (close / df["ath_to_date"] - 1) * 100
    for days in [30, 90, 365]:
        rolling_high = close.rolling(days).max()
        df[f"drawdown_{days}d_pct"] = (close / rolling_high - 1) * 100

    daily_return = close.pct_change()
    for days in [7, 30, 90]:
        df[f"volatility_{days}d_pct"] = daily_return.rolling(days).std() * np.sqrt(365) * 100
    return df
