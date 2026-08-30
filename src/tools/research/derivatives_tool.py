from __future__ import annotations

from datetime import datetime, timezone

import requests

BASE = "https://fapi.binance.com"
TIMEOUT = 8


def _get(path: str, params: dict | None = None):
    response = requests.get(f"{BASE}{path}", params=params or {}, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def _float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def fetch_btc_derivatives(symbol: str = "BTCUSDT") -> dict:
    result = {"available": False, "provider": "Binance USD-M Futures", "symbol": symbol, "errors": []}
    try:
        premium = _get("/fapi/v1/premiumIndex", {"symbol": symbol})
        result.update({
            "mark_price": _float(premium.get("markPrice")),
            "funding_rate": _float(premium.get("lastFundingRate")),
            "next_funding_time": premium.get("nextFundingTime"),
        })
    except Exception as exc:
        result["errors"].append(f"funding: {exc}")

    try:
        oi = _get("/fapi/v1/openInterest", {"symbol": symbol})
        result["open_interest"] = _float(oi.get("openInterest"))
    except Exception as exc:
        result["errors"].append(f"open_interest: {exc}")

    try:
        hist = _get("/futures/data/openInterestHist", {"symbol": symbol, "period": "1h", "limit": 25})
        values = [_float(x.get("sumOpenInterestValue")) for x in hist]
        values = [x for x in values if x is not None]
        if len(values) >= 2 and values[0] != 0:
            result["open_interest_value_usd"] = values[-1]
            result["open_interest_change_24h_pct"] = (values[-1] / values[0] - 1) * 100
    except Exception as exc:
        result["errors"].append(f"open_interest_history: {exc}")

    endpoints = {
        "global_long_short_ratio": "/futures/data/globalLongShortAccountRatio",
        "top_trader_position_ratio": "/futures/data/topLongShortPositionRatio",
        "taker_buy_sell_ratio": "/futures/data/takerlongshortRatio",
    }
    for key, path in endpoints.items():
        try:
            payload = _get(path, {"symbol": symbol, "period": "1h", "limit": 2})
            latest = payload[-1] if isinstance(payload, list) and payload else {}
            if key == "taker_buy_sell_ratio":
                result[key] = _float(latest.get("buySellRatio"))
            else:
                result[key] = _float(latest.get("longShortRatio"))
        except Exception as exc:
            result["errors"].append(f"{key}: {exc}")

    result["available"] = any(result.get(k) is not None for k in ["funding_rate", "open_interest", "global_long_short_ratio"])
    result["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return result
