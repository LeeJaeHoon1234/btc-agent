from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd


def _safe_float(value, default=None):
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out.loc[(avg_loss == 0) & (avg_gain > 0)] = 100
    return out


def add_intraday_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich an OHLCV frame without assigning trading meaning to the values."""
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy().sort_values("date").reset_index(drop=True)
    close = out["close"].astype(float)
    high = out["high"].astype(float)
    low = out["low"].astype(float)
    volume = out["volume"].astype(float)

    out["return_1bar_pct"] = close.pct_change() * 100
    for bars in (3, 5, 12, 24, 48, 96, 144):
        out[f"return_{bars}bar_pct"] = (close / close.shift(bars) - 1) * 100

    out["ema9"] = close.ewm(span=9, adjust=False).mean()
    out["ema21"] = close.ewm(span=21, adjust=False).mean()
    out["ema50"] = close.ewm(span=50, adjust=False).mean()
    out["ema200"] = close.ewm(span=200, adjust=False).mean()
    out["rsi14"] = _rsi(close)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    out["macd"] = ema12 - ema26
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]

    basis = close.rolling(20).mean()
    dev = close.rolling(20).std(ddof=0)
    out["bb_mid"] = basis
    out["bb_upper"] = basis + 2 * dev
    out["bb_lower"] = basis - 2 * dev
    out["bb_width_pct"] = (out["bb_upper"] - out["bb_lower"]) / basis * 100
    out["bb_position"] = (close - out["bb_lower"]) / (out["bb_upper"] - out["bb_lower"])

    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    out["atr14"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    out["atr14_pct"] = out["atr14"] / close * 100

    typical = (high + low + close) / 3
    # Rolling VWAP keeps an intraday-style reference even when a frame spans >1 day.
    pv = typical * volume
    out["vwap_48"] = pv.rolling(48, min_periods=1).sum() / volume.rolling(48, min_periods=1).sum().replace(0, np.nan)
    out["vwap_gap_pct"] = (close / out["vwap_48"] - 1) * 100

    out["volume_ma20"] = volume.rolling(20).mean()
    out["volume_ratio"] = volume / out["volume_ma20"]
    rolling_mean = volume.rolling(48).mean()
    rolling_std = volume.rolling(48).std(ddof=0).replace(0, np.nan)
    out["volume_zscore"] = (volume - rolling_mean) / rolling_std

    returns = close.pct_change()
    out["realized_vol_12"] = returns.rolling(12).std(ddof=0) * math.sqrt(12) * 100
    out["realized_vol_48"] = returns.rolling(48).std(ddof=0) * math.sqrt(48) * 100

    rolling_high = high.rolling(48, min_periods=1).max()
    rolling_low = low.rolling(48, min_periods=1).min()
    out["pullback_from_48bar_high_pct"] = (close / rolling_high - 1) * 100
    out["rebound_from_48bar_low_pct"] = (close / rolling_low - 1) * 100
    out["range_position_48"] = (close - rolling_low) / (rolling_high - rolling_low).replace(0, np.nan)
    return out


def latest_metrics(df: pd.DataFrame, *, minutes_per_bar: int = 5) -> dict:
    if df is None or df.empty:
        return {}
    enriched = add_intraday_indicators(df)
    row = enriched.iloc[-1]
    close = _safe_float(row.get("close"))

    def ret_minutes(minutes: int):
        bars = max(1, int(round(minutes / minutes_per_bar)))
        if len(enriched) <= bars:
            return None
        previous = _safe_float(enriched.iloc[-1 - bars].get("close"))
        if close is None or previous in {None, 0}:
            return None
        return (close / previous - 1) * 100

    metrics = {
        "price": close,
        "return_5m_pct": ret_minutes(5),
        "return_15m_pct": ret_minutes(15),
        "return_1h_pct": ret_minutes(60),
        "return_4h_pct": ret_minutes(240),
        "rsi14": _safe_float(row.get("rsi14")),
        "ema9_gap_pct": None if close is None or not _safe_float(row.get("ema9")) else (close / float(row["ema9"]) - 1) * 100,
        "ema21_gap_pct": None if close is None or not _safe_float(row.get("ema21")) else (close / float(row["ema21"]) - 1) * 100,
        "macd_hist": _safe_float(row.get("macd_hist")),
        "bb_position": _safe_float(row.get("bb_position")),
        "bb_width_pct": _safe_float(row.get("bb_width_pct")),
        "atr14_pct": _safe_float(row.get("atr14_pct")),
        "vwap_gap_pct": _safe_float(row.get("vwap_gap_pct")),
        "volume_ratio": _safe_float(row.get("volume_ratio")),
        "volume_zscore": _safe_float(row.get("volume_zscore")),
        "realized_vol": _safe_float(row.get("realized_vol_48")),
        "pullback_from_recent_high_pct": _safe_float(row.get("pullback_from_48bar_high_pct")),
        "rebound_from_recent_low_pct": _safe_float(row.get("rebound_from_48bar_low_pct")),
        "range_position": _safe_float(row.get("range_position_48")),
        "candle_time": str(row.get("date")),
    }
    return metrics


def summarize_series(df: pd.DataFrame, points: int = 144) -> list[dict]:
    if df is None or df.empty:
        return []
    cols: Iterable[str] = [c for c in ("date", "open", "high", "low", "close", "volume") if c in df.columns]
    recent = df[list(cols)].tail(points)
    rows = []
    for item in recent.to_dict(orient="records"):
        rows.append({k: (v.isoformat() if isinstance(v, pd.Timestamp) else _safe_float(v, v)) for k, v in item.items()})
    return rows
