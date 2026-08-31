from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import math
import requests

BINANCE = "https://fapi.binance.com"
BYBIT = "https://api.bybit.com"
TIMEOUT = 4


def _float(value, default=None):
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _get(base: str, path: str, params: dict | None = None):
    response = requests.get(f"{base}{path}", params=params or {}, timeout=TIMEOUT, headers={"User-Agent": "btc-agent-v4/4.0"})
    response.raise_for_status()
    return response.json()


def _binance(symbol: str) -> dict:
    result = {"available": False, "provider": "Binance USD-M Futures", "symbol": symbol, "errors": []}
    specs = {
        "premium": ("/fapi/v1/premiumIndex", {"symbol": symbol}),
        "oi": ("/fapi/v1/openInterest", {"symbol": symbol}),
        "oi_hist": ("/futures/data/openInterestHist", {"symbol": symbol, "period": "1h", "limit": 25}),
        "global_ls": ("/futures/data/globalLongShortAccountRatio", {"symbol": symbol, "period": "1h", "limit": 2}),
        "top_ls": ("/futures/data/topLongShortPositionRatio", {"symbol": symbol, "period": "1h", "limit": 2}),
        "taker": ("/futures/data/takerlongshortRatio", {"symbol": symbol, "period": "1h", "limit": 2}),
        "basis": ("/futures/data/basis", {"pair": symbol, "contractType": "PERPETUAL", "period": "1h", "limit": 2}),
    }
    payloads = {}
    with ThreadPoolExecutor(max_workers=len(specs)) as pool:
        jobs = {pool.submit(_get, BINANCE, path, params): name for name, (path, params) in specs.items()}
        for future in as_completed(jobs):
            name = jobs[future]
            try: payloads[name] = future.result()
            except Exception as exc: result["errors"].append(f"{name}: {type(exc).__name__}: {exc}")

    premium = payloads.get("premium", {})
    result.update({"mark_price": _float(premium.get("markPrice")), "index_price": _float(premium.get("indexPrice")), "funding_rate": _float(premium.get("lastFundingRate")), "next_funding_time": premium.get("nextFundingTime")})
    result["open_interest"] = _float(payloads.get("oi", {}).get("openInterest"))
    hist = payloads.get("oi_hist", []) if isinstance(payloads.get("oi_hist", []), list) else []
    values = [_float(x.get("sumOpenInterestValue")) for x in hist]; values = [x for x in values if x is not None]
    if len(values) >= 2 and values[0] != 0:
        result["open_interest_value_usd"] = values[-1]; result["open_interest_change_24h_pct"] = (values[-1] / values[0] - 1) * 100
    for src, key, field in [("global_ls", "global_long_short_ratio", "longShortRatio"), ("top_ls", "top_trader_position_ratio", "longShortRatio"), ("taker", "taker_buy_sell_ratio", "buySellRatio")]:
        rows = payloads.get(src, []) if isinstance(payloads.get(src, []), list) else []
        result[key] = _float(rows[-1].get(field)) if rows else None
    basis = payloads.get("basis", []) if isinstance(payloads.get("basis", []), list) else []
    result["basis_rate"] = _float(basis[-1].get("basisRate")) if basis else None
    result["available"] = any(result.get(k) is not None for k in ["funding_rate", "open_interest", "global_long_short_ratio", "taker_buy_sell_ratio"])
    return result


def _bybit(symbol: str) -> dict:
    result = {"available": False, "provider": "Bybit Linear Futures fallback", "symbol": symbol, "errors": []}
    specs = {
        "ticker": ("/v5/market/tickers", {"category": "linear", "symbol": symbol}),
        "oi_hist": ("/v5/market/open-interest", {"category": "linear", "symbol": symbol, "intervalTime": "1h", "limit": 25}),
        "ratio": ("/v5/market/account-ratio", {"category": "linear", "symbol": symbol, "period": "1h", "limit": 2}),
    }
    payloads = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(_get, BYBIT, path, params): name for name, (path, params) in specs.items()}
        for future in as_completed(jobs):
            name = jobs[future]
            try: payloads[name] = future.result()
            except Exception as exc: result["errors"].append(f"{name}: {type(exc).__name__}: {exc}")
    rows = payloads.get("ticker", {}).get("result", {}).get("list", []) if isinstance(payloads.get("ticker"), dict) else []
    x = rows[0] if rows else {}
    result.update({
        "mark_price": _float(x.get("markPrice")), "index_price": _float(x.get("indexPrice")), "funding_rate": _float(x.get("fundingRate")),
        "next_funding_time": x.get("nextFundingTime"), "open_interest": _float(x.get("openInterest")), "open_interest_value_usd": _float(x.get("openInterestValue")),
        "basis_rate": _float(x.get("basisRate")), "price_change_24h_pct": (_float(x.get("price24hPcnt"), 0.0) or 0.0) * 100,
    })
    oi_rows = payloads.get("oi_hist", {}).get("result", {}).get("list", []) if isinstance(payloads.get("oi_hist"), dict) else []
    vals = [_float(x.get("openInterest")) for x in reversed(oi_rows)]; vals = [x for x in vals if x is not None]
    if len(vals) >= 2 and vals[0] != 0: result["open_interest_change_24h_pct"] = (vals[-1] / vals[0] - 1) * 100
    ratio_rows = payloads.get("ratio", {}).get("result", {}).get("list", []) if isinstance(payloads.get("ratio"), dict) else []
    if ratio_rows:
        latest = ratio_rows[0]
        buy = _float(latest.get("buyRatio")); sell = _float(latest.get("sellRatio"))
        result["global_long_short_ratio"] = (buy / sell) if buy is not None and sell not in {None, 0} else None
    result["available"] = any(result.get(k) is not None for k in ["funding_rate", "open_interest", "open_interest_change_24h_pct"])
    return result


def fetch_btc_derivatives(symbol: str = "BTCUSDT") -> dict:
    primary = _binance(symbol)
    if primary.get("available"):
        primary.update({"fetched_at": datetime.now(timezone.utc).isoformat(), "fallback_used": False})
        return primary
    fallback = _bybit(symbol)
    fallback.update({"primary_errors": primary.get("errors", []), "fallback_used": True, "fetched_at": datetime.now(timezone.utc).isoformat()})
    return fallback
