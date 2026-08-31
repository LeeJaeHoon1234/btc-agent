from __future__ import annotations

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import time

import numpy as np
import pandas as pd
import requests

from src.tools.intraday_indicators import latest_metrics, summarize_series

BASE_URL = "https://api.upbit.com/v1"
TIMEOUT = 7
HEADERS = {"User-Agent": "btc-agent-v4/4.0"}


def _get(path: str, params: dict | None = None):
    r = requests.get(f"{BASE_URL}{path}", params=params or {}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _f(value, default=None):
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _normalize_minutes(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    out = pd.DataFrame(rows)
    wanted = {
        "candle_date_time_kst": "date",
        "opening_price": "open",
        "high_price": "high",
        "low_price": "low",
        "trade_price": "close",
        "candle_acc_trade_volume": "volume",
    }
    out = out[list(wanted)].rename(columns=wanted)
    out["date"] = pd.to_datetime(out["date"])
    return out.sort_values("date").drop_duplicates("date").reset_index(drop=True)


def fetch_minute_candles(market: str = "KRW-BTC", unit: int = 5, count: int = 200) -> pd.DataFrame:
    return _normalize_minutes(_get(f"/candles/minutes/{unit}", {"market": market, "count": min(count, 200)}))


def fetch_ticker(market: str = "KRW-BTC") -> dict:
    rows = _get("/ticker", {"markets": market})
    row = rows[0] if rows else {}
    return {
        "price": _f(row.get("trade_price")),
        "change_24h_pct": (_f(row.get("signed_change_rate"), 0.0) or 0.0) * 100,
        "high_24h": _f(row.get("high_price")),
        "low_24h": _f(row.get("low_price")),
        "opening_price": _f(row.get("opening_price")),
        "volume_24h": _f(row.get("acc_trade_volume_24h")),
        "value_24h_krw": _f(row.get("acc_trade_price_24h")),
        "trade_timestamp": row.get("timestamp"),
    }


def fetch_orderbook(market: str = "KRW-BTC", count: int = 15) -> dict:
    rows = _get("/orderbook", {"markets": market, "count": min(max(1, count), 30)})
    row = rows[0] if rows else {}
    units = row.get("orderbook_units", [])
    bid = sum(_f(x.get("bid_size"), 0.0) or 0.0 for x in units)
    ask = sum(_f(x.get("ask_size"), 0.0) or 0.0 for x in units)
    denom = bid + ask
    imbalance = (bid - ask) / denom if denom else None
    best_bid = _f(units[0].get("bid_price")) if units else None
    best_ask = _f(units[0].get("ask_price")) if units else None
    mid = (best_bid + best_ask) / 2 if best_bid and best_ask else None
    spread_bps = ((best_ask - best_bid) / mid * 10000) if mid and best_ask and best_bid else None
    return {
        "bid_size": bid,
        "ask_size": ask,
        "imbalance": imbalance,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread_bps": spread_bps,
    }


def fetch_recent_trades(market: str = "KRW-BTC", count: int = 200) -> dict:
    rows = _get("/trades/ticks", {"market": market, "count": min(max(20, count), 500)})
    bid_volume = 0.0
    ask_volume = 0.0
    signed_value = 0.0
    for row in rows:
        vol = _f(row.get("trade_volume"), 0.0) or 0.0
        price = _f(row.get("trade_price"), 0.0) or 0.0
        side = str(row.get("ask_bid", "")).upper()
        if side == "BID":
            bid_volume += vol
            signed_value += vol * price
        elif side == "ASK":
            ask_volume += vol
            signed_value -= vol * price
    ratio = bid_volume / ask_volume if ask_volume else (float("inf") if bid_volume else None)
    return {
        "aggressive_buy_volume": bid_volume,
        "aggressive_sell_volume": ask_volume,
        "taker_buy_sell_ratio": ratio if ratio != float("inf") else None,
        "signed_trade_value_krw": signed_value,
        "sample_count": len(rows),
    }


def _day_context(ticker: dict) -> dict:
    price = ticker.get("price")
    high = ticker.get("high_24h")
    low = ticker.get("low_24h")
    rebound = (price / low - 1) * 100 if price and low else None
    pullback = (price / high - 1) * 100 if price and high else None
    pos = (price - low) / (high - low) if price and high and low and high != low else None
    return {
        "rebound_from_24h_low_pct": rebound,
        "pullback_from_24h_high_pct": pullback,
        "position_in_24h_range": pos,
    }


def fetch_live_market_snapshot(market: str = "KRW-BTC") -> dict:
    """Best-effort fast market snapshot. Individual upstream failures do not kill the whole response."""
    started = time.monotonic()
    out = {"available": False, "provider": "Upbit", "market": market, "errors": []}
    ticker, orderbook, trades = {}, {}, {}
    frame_1m, frame_5m = pd.DataFrame(), pd.DataFrame()

    jobs = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        for name, fn in (
            ("ticker", lambda: fetch_ticker(market)),
            ("orderbook", lambda: fetch_orderbook(market)),
            ("trades", lambda: fetch_recent_trades(market)),
            ("candles_1m", lambda: fetch_minute_candles(market, 1, 200)),
            ("candles_5m", lambda: fetch_minute_candles(market, 5, 200)),
        ):
            jobs[pool.submit(fn)] = name
        for future in as_completed(jobs):
            name = jobs[future]
            try:
                result = future.result()
                if name == "ticker": ticker = result
                elif name == "orderbook": orderbook = result
                elif name == "trades": trades = result
                elif name == "candles_1m": frame_1m = result
                else: frame_5m = result
            except Exception as exc:
                out["errors"].append(f"{name}: {type(exc).__name__}: {exc}")

    fast = latest_metrics(frame_1m, minutes_per_bar=1) if not frame_1m.empty else {}
    slower = latest_metrics(frame_5m, minutes_per_bar=5) if not frame_5m.empty else {}
    metrics = dict(slower)
    # 1-minute frame owns truly short-horizon features; 5-minute frame supplies 4h / broader context.
    for key in ["price", "return_5m_pct", "return_15m_pct", "return_1h_pct", "rsi14", "ema9_gap_pct", "ema21_gap_pct", "macd_hist", "bb_position", "bb_width_pct", "atr14_pct", "vwap_gap_pct", "volume_ratio", "volume_zscore", "spot_taker_buy_sell_ratio"]:
        if fast.get(key) is not None:
            metrics[key] = fast[key]
    metrics.update(_day_context(ticker))
    if ticker.get("change_24h_pct") is not None: metrics["return_24h_pct"] = ticker["change_24h_pct"]
    if orderbook:
        metrics["orderbook_imbalance"] = orderbook.get("imbalance")
        metrics["spread_bps"] = orderbook.get("spread_bps")
    if trades: metrics["spot_taker_buy_sell_ratio"] = trades.get("taker_buy_sell_ratio")

    out.update({
        "available": bool(ticker or metrics), "ticker": ticker, "metrics": metrics, "orderbook": orderbook, "trades": trades,
        "series_1m": summarize_series(frame_1m, 120), "series_5m": summarize_series(frame_5m, 144),
        "fetched_at": datetime.now(timezone.utc).isoformat(), "latency_ms": round((time.monotonic() - started) * 1000),
    })
    return out


def make_demo_live_snapshot(daily_df: pd.DataFrame | None = None, seed: int = 11) -> dict:
    rng = np.random.default_rng(seed)
    base = float(daily_df["close"].iloc[-1]) if daily_df is not None and not daily_df.empty else 100_000_000.0
    periods = 200
    dates = pd.date_range(end=pd.Timestamp.now().floor("5min"), periods=periods, freq="5min")
    t = np.arange(periods)
    # Intentionally contains a flush and recovery so event detection can be exercised offline.
    drift = rng.normal(0.00002, 0.0012, periods)
    drift[-36:-27] -= 0.0032
    drift[-27:-13] += 0.0030
    close = base * np.exp(np.cumsum(drift) - np.cumsum(drift)[-1])
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1 + rng.uniform(0.0002, 0.0018, periods))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.0002, 0.0018, periods))
    volume = rng.lognormal(2.8, 0.45, periods)
    volume[-36:-12] *= 2.1
    frame = pd.DataFrame({"date": dates, "open": open_, "high": high, "low": low, "close": close, "volume": volume})
    metrics = latest_metrics(frame, minutes_per_bar=5)
    h24, l24 = float(frame.high.max()), float(frame.low.min())
    price = float(frame.close.iloc[-1])
    ticker = {
        "price": price,
        "change_24h_pct": float((price / frame.close.iloc[0] - 1) * 100),
        "high_24h": h24,
        "low_24h": l24,
        "opening_price": float(frame.close.iloc[0]),
        "volume_24h": float(frame.volume.sum()),
        "value_24h_krw": float((frame.close * frame.volume).sum()),
        "trade_timestamp": int(pd.Timestamp.now().timestamp() * 1000),
    }
    metrics.update(_day_context(ticker))
    metrics["return_24h_pct"] = ticker["change_24h_pct"]
    metrics["orderbook_imbalance"] = 0.12
    metrics["spread_bps"] = 1.3
    metrics["spot_taker_buy_sell_ratio"] = 1.18
    return {
        "available": True, "provider": "demo", "market": "KRW-BTC", "ticker": ticker,
        "metrics": metrics, "orderbook": {"imbalance": 0.12, "spread_bps": 1.3},
        "trades": {"taker_buy_sell_ratio": 1.18, "sample_count": 200},
        "series_5m": summarize_series(frame, 144), "errors": [],
        "fetched_at": datetime.now(timezone.utc).isoformat(), "latency_ms": 0,
    }
