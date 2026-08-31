from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import math
import time

import numpy as np
import pandas as pd
import requests

from src.tools.intraday_indicators import latest_metrics, summarize_series

UPBIT_BASE_URL = "https://api.upbit.com/v1"
COINBASE_TICKER_URL = "https://api.exchange.coinbase.com/products/BTC-USD/ticker"
TIMEOUT = 7
HEADERS = {"User-Agent": "btc-agent-v4.1/4.1"}


def _get(path: str, params: dict | None = None):
    r = requests.get(f"{UPBIT_BASE_URL}{path}", params=params or {}, headers=HEADERS, timeout=TIMEOUT)
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
    change_from_prev = (_f(row.get("signed_change_rate"), 0.0) or 0.0) * 100
    day_high = _f(row.get("high_price"))
    day_low = _f(row.get("low_price"))
    day_open = _f(row.get("opening_price"))
    return {
        "price": _f(row.get("trade_price")),
        "change_since_prev_close_pct": change_from_prev,
        # Backward-compatible alias. V4.1 UI no longer labels this as rolling 24h.
        "change_24h_pct": change_from_prev,
        "day_high": day_high,
        "day_low": day_low,
        "day_open": day_open,
        "high_24h": day_high,
        "low_24h": day_low,
        "opening_price": day_open,
        "volume_24h": _f(row.get("acc_trade_volume_24h")),
        "value_24h_krw": _f(row.get("acc_trade_price_24h")),
        "trade_timestamp": row.get("timestamp"),
    }


def fetch_usd_ticker() -> dict:
    """Independent BTC/USD reference price. It is never used as the KRW trading price."""
    r = requests.get(COINBASE_TICKER_URL, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    row = r.json() or {}
    return {
        "price_usd": _f(row.get("price")),
        "provider": "Coinbase BTC-USD",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
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
    high = ticker.get("day_high") or ticker.get("high_24h")
    low = ticker.get("day_low") or ticker.get("low_24h")
    rebound = (price / low - 1) * 100 if price and low else None
    pullback = (price / high - 1) * 100 if price and high else None
    pos = (price - low) / (high - low) if price and high and low and high != low else None
    return {
        "rebound_from_24h_low_pct": rebound,
        "pullback_from_24h_high_pct": pullback,
        "position_in_24h_range": pos,
    }


def _move_label(value: float | None, horizon: str) -> str:
    if value is None:
        return "값 확인 중"
    a = abs(value)
    if a < 0.15:
        return "거의 움직임 없음"
    if value > 0:
        if a >= 2.0:
            return "강하게 오르는 중"
        if a >= 0.7:
            return "상승 흐름"
        return "소폭 오르는 중"
    if a >= 2.0:
        return "강하게 밀리는 중"
    if a >= 0.7:
        return "하락 흐름"
    return "소폭 눌리는 중"


def _day_position_label(position: float | None) -> str:
    if position is None:
        return "오늘 위치 확인 중"
    if position >= 0.85:
        return "일중 고점 부근"
    if position >= 0.60:
        return "일중 범위 상단"
    if position >= 0.40:
        return "일중 범위 중간"
    if position >= 0.15:
        return "일중 범위 하단"
    return "일중 저점 부근"


def _validate_snapshot(ticker: dict, metrics: dict, frame_1m: pd.DataFrame, usd: dict) -> dict:
    warnings: list[str] = []
    checks: dict[str, bool] = {}
    price = _f(ticker.get("price"))
    high = _f(ticker.get("high_24h"))
    low = _f(ticker.get("low_24h"))

    checks["positive_price"] = bool(price and price > 0)
    checks["valid_day_range"] = bool(high and low and high >= low > 0)
    checks["price_inside_day_range"] = bool(price and high and low and low <= price <= high)
    if not checks["positive_price"]:
        warnings.append("현재 가격이 유효하지 않습니다.")
    if high is not None and low is not None and high < low:
        warnings.append("24시간 고가/저가 관계가 비정상입니다.")
    if price and high and low and not (low <= price <= high):
        warnings.append("현재가가 제공된 24시간 고가/저가 범위를 벗어났습니다.")

    pos = _f(metrics.get("position_in_24h_range"))
    checks["range_position_consistent"] = pos is None or -0.02 <= pos <= 1.02
    if not checks["range_position_consistent"]:
        warnings.append("일중 범위 내 현재 위치 계산이 일관되지 않습니다.")

    candle_gap_pct = None
    if price and frame_1m is not None and not frame_1m.empty:
        last_close = _f(frame_1m.iloc[-1].get("close"))
        if last_close:
            candle_gap_pct = (price / last_close - 1) * 100
            checks["ticker_vs_1m_close"] = abs(candle_gap_pct) <= 1.5
            if not checks["ticker_vs_1m_close"]:
                warnings.append(f"실시간 가격과 최신 1분봉 종가가 {abs(candle_gap_pct):.2f}% 차이납니다.")

    usd_price = _f(usd.get("price_usd"))
    checks["usd_reference_available"] = bool(usd_price and usd_price > 0)
    implied_krw_per_usd = price / usd_price if price and usd_price else None
    if implied_krw_per_usd and not (500 <= implied_krw_per_usd <= 3000):
        warnings.append("원화/달러 BTC 가격의 환산 관계가 평소 범위를 크게 벗어났습니다.")
        checks["krw_usd_crosscheck"] = False
    elif implied_krw_per_usd:
        checks["krw_usd_crosscheck"] = True

    return {
        "status": "warning" if warnings else "ok",
        "checks": checks,
        "warnings": warnings,
        "ticker_vs_1m_close_gap_pct": candle_gap_pct,
        "implied_krw_per_usd": implied_krw_per_usd,
    }


def _friendly_view(ticker: dict, metrics: dict) -> dict:
    r1 = _f(metrics.get("return_1h_pct"))
    r4 = _f(metrics.get("return_4h_pct"))
    pos = _f(metrics.get("position_in_24h_range"))
    rebound = _f(metrics.get("rebound_from_24h_low_pct"))
    pullback = _f(metrics.get("pullback_from_24h_high_pct"))
    if r1 is None and r4 is None:
        headline = "단기 흐름을 확인하고 있습니다."
    elif (r1 or 0) < -0.2 and (r4 or 0) > 0.2:
        headline = "방금은 조금 밀렸지만, 최근 몇 시간 흐름은 아직 플러스입니다."
    elif (r1 or 0) > 0.2 and (r4 or 0) < -0.2:
        headline = "방금 반등 중이지만, 최근 몇 시간 하락을 아직 다 되돌리진 못했습니다."
    elif (r1 or 0) > 0.2 and (r4 or 0) > 0.2:
        headline = "짧은 시간과 최근 몇 시간 모두 상승 쪽입니다."
    elif (r1 or 0) < -0.2 and (r4 or 0) < -0.2:
        headline = "짧은 시간과 최근 몇 시간 모두 약한 흐름입니다."
    else:
        headline = "단기 방향은 아직 뚜렷하지 않습니다."

    return {
        "headline": headline,
        "cards": {
            "1h": {"label": "최근 1시간", "value_pct": r1, "meaning": _move_label(r1, "1h")},
            "4h": {"label": "최근 4시간", "value_pct": r4, "meaning": _move_label(r4, "4h")},
            "from_low": {"label": "일중 저점에서", "value_pct": rebound, "meaning": "저점에서 회복한 폭" if rebound is not None else "확인 중"},
            "from_high": {"label": "일중 고점에서", "value_pct": pullback, "meaning": "고점과 남은 거리" if pullback is not None else "확인 중"},
        },
        "day_position": {
            "label": _day_position_label(pos),
            "position": pos,
            "low": ticker.get("low_24h"),
            "current": ticker.get("price"),
            "high": ticker.get("high_24h"),
        },
    }


def fetch_live_market_snapshot(market: str = "KRW-BTC") -> dict:
    """Best-effort fast snapshot. Independent upstream failures never invalidate the whole response."""
    started = time.monotonic()
    out = {"available": False, "provider": "Upbit", "market": market, "errors": []}
    ticker, usd, orderbook, trades = {}, {}, {}, {}
    frame_1m, frame_5m, frame_60m = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    jobs = {}
    with ThreadPoolExecutor(max_workers=7) as pool:
        for name, fn in (
            ("ticker", lambda: fetch_ticker(market)),
            ("usd", fetch_usd_ticker),
            ("orderbook", lambda: fetch_orderbook(market)),
            ("trades", lambda: fetch_recent_trades(market)),
            ("candles_1m", lambda: fetch_minute_candles(market, 1, 200)),
            ("candles_5m", lambda: fetch_minute_candles(market, 5, 200)),
            ("candles_60m", lambda: fetch_minute_candles(market, 60, 72)),
        ):
            jobs[pool.submit(fn)] = name
        for future in as_completed(jobs):
            name = jobs[future]
            try:
                result = future.result()
                if name == "ticker": ticker = result
                elif name == "usd": usd = result
                elif name == "orderbook": orderbook = result
                elif name == "trades": trades = result
                elif name == "candles_1m": frame_1m = result
                elif name == "candles_5m": frame_5m = result
                else: frame_60m = result
            except Exception as exc:
                out["errors"].append(f"{name}: {type(exc).__name__}: {exc}")

    fast = latest_metrics(frame_1m, minutes_per_bar=1) if not frame_1m.empty else {}
    slower = latest_metrics(frame_5m, minutes_per_bar=5) if not frame_5m.empty else {}
    metrics = dict(slower)
    for key in ["price", "return_5m_pct", "return_15m_pct", "return_1h_pct", "rsi14", "ema9_gap_pct", "ema21_gap_pct", "macd_hist", "bb_position", "bb_width_pct", "atr14_pct", "vwap_gap_pct", "volume_ratio", "volume_zscore", "spot_taker_buy_sell_ratio"]:
        if fast.get(key) is not None:
            metrics[key] = fast[key]
    metrics.update(_day_context(ticker))
    hourly = latest_metrics(frame_60m, minutes_per_bar=60) if not frame_60m.empty else {}
    if hourly.get("return_4h_pct") is not None and metrics.get("return_4h_pct") is None:
        metrics["return_4h_pct"] = hourly.get("return_4h_pct")
    if not frame_60m.empty and len(frame_60m) >= 25:
        current = _f(ticker.get("price")) or _f(frame_60m.iloc[-1].get("close"))
        prev24 = _f(frame_60m.iloc[-25].get("close"))
        if current and prev24:
            metrics["return_24h_pct"] = (current / prev24 - 1) * 100
        last24 = frame_60m.tail(24)
        metrics["rolling_24h_high"] = _f(last24["high"].max())
        metrics["rolling_24h_low"] = _f(last24["low"].min())
    metrics["change_since_prev_close_pct"] = ticker.get("change_since_prev_close_pct")
    if orderbook:
        metrics["orderbook_imbalance"] = orderbook.get("imbalance")
        metrics["spread_bps"] = orderbook.get("spread_bps")
    if trades:
        metrics["spot_taker_buy_sell_ratio"] = trades.get("taker_buy_sell_ratio")

    if usd.get("price_usd") is not None:
        ticker["price_usd"] = usd["price_usd"]
        ticker["usd_provider"] = usd.get("provider")
        ticker["usd_fetched_at"] = usd.get("fetched_at")

    validation = _validate_snapshot(ticker, metrics, frame_1m, usd)
    friendly = _friendly_view(ticker, metrics)
    out.update({
        "available": bool(ticker or metrics),
        "ticker": ticker,
        "metrics": metrics,
        "orderbook": orderbook,
        "trades": trades,
        "series_1m": summarize_series(frame_1m, 180),
        "series_5m": summarize_series(frame_5m, 200),
        "series_60m": summarize_series(frame_60m, 72),
        "friendly": friendly,
        "validation": validation,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "latency_ms": round((time.monotonic() - started) * 1000),
    })
    return out


def make_demo_live_snapshot(daily_df: pd.DataFrame | None = None, seed: int = 11) -> dict:
    rng = np.random.default_rng(seed)
    base = float(daily_df["close"].iloc[-1]) if daily_df is not None and not daily_df.empty else 100_000_000.0
    periods = 4320
    dates = pd.date_range(end=pd.Timestamp.now().floor("1min"), periods=periods, freq="1min")
    drift = rng.normal(0.00002, 0.00065, periods)
    drift[-80:-62] -= 0.0012
    drift[-62:-30] += 0.0010
    close = base * np.exp(np.cumsum(drift) - np.cumsum(drift)[-1])
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1 + rng.uniform(0.0001, 0.0009, periods))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.0001, 0.0009, periods))
    volume = rng.lognormal(2.8, 0.45, periods)
    volume[-80:-30] *= 2.1
    frame_1m = pd.DataFrame({"date": dates, "open": open_, "high": high, "low": low, "close": close, "volume": volume})
    frame_5m = frame_1m.set_index("date").resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna().reset_index()
    metrics = latest_metrics(frame_1m, minutes_per_bar=1)
    slower = latest_metrics(frame_5m, minutes_per_bar=5)
    if slower.get("return_4h_pct") is not None:
        metrics["return_4h_pct"] = slower["return_4h_pct"]
    current_day = frame_1m[frame_1m["date"].dt.date == frame_1m["date"].iloc[-1].date()]
    if current_day.empty:
        current_day = frame_1m.tail(1440)
    h24, l24 = float(current_day.high.max()), float(current_day.low.min())
    price = float(frame_1m.close.iloc[-1])
    usd_price = price / 1365.0
    ticker = {
        "price": price,
        "price_usd": usd_price,
        "usd_provider": "demo",
        "usd_fetched_at": datetime.now(timezone.utc).isoformat(),
        "change_since_prev_close_pct": float((price / current_day.close.iloc[0] - 1) * 100),
        "change_24h_pct": float((price / frame_1m.close.iloc[-1441] - 1) * 100),
        "day_high": h24,
        "day_low": l24,
        "day_open": float(current_day.close.iloc[0]),
        "high_24h": h24,
        "low_24h": l24,
        "opening_price": float(frame_1m.close.iloc[0]),
        "volume_24h": float(frame_1m.volume.sum()),
        "value_24h_krw": float((frame_1m.close * frame_1m.volume).sum()),
        "trade_timestamp": int(pd.Timestamp.now().timestamp() * 1000),
    }
    metrics.update(_day_context(ticker))
    metrics["return_24h_pct"] = ticker["change_24h_pct"]
    metrics["change_since_prev_close_pct"] = ticker["change_since_prev_close_pct"]
    metrics["orderbook_imbalance"] = 0.12
    metrics["spread_bps"] = 1.3
    metrics["spot_taker_buy_sell_ratio"] = 1.18
    validation = _validate_snapshot(ticker, metrics, frame_1m, {"price_usd": usd_price})
    frame_60m = frame_1m.set_index("date").resample("60min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna().reset_index()
    return {
        "available": True,
        "provider": "demo",
        "market": "KRW-BTC",
        "ticker": ticker,
        "metrics": metrics,
        "orderbook": {"imbalance": 0.12, "spread_bps": 1.3},
        "trades": {"taker_buy_sell_ratio": 1.18, "sample_count": 200},
        "series_1m": summarize_series(frame_1m, 180),
        "series_5m": summarize_series(frame_5m, 200),
        "series_60m": summarize_series(frame_60m, 72),
        "friendly": _friendly_view(ticker, metrics),
        "validation": validation,
        "errors": [],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "latency_ms": 0,
    }
