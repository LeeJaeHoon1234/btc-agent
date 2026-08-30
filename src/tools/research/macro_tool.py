from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

TIMEOUT = 8


def _pct_change(values: list[float]) -> float | None:
    if len(values) < 2 or values[0] == 0:
        return None
    return (values[-1] / values[0] - 1) * 100


def _fred_series(series_id: str, api_key: str, limit: int = 8) -> list[dict]:
    response = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("observations", [])


def _yahoo_chart(symbol: str) -> list[float]:
    response = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"range": "1mo", "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()["chart"]["result"][0]
    closes = data["indicators"]["quote"][0]["close"]
    return [float(x) for x in closes if x is not None]


def fetch_macro_snapshot() -> dict:
    out = {"available": False, "provider": None, "errors": []}
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if api_key:
        try:
            # Broad Trade Weighted U.S. Dollar Index + 10Y Treasury yield.
            dollar_obs = _fred_series("DTWEXBGS", api_key)
            yield_obs = _fred_series("DGS10", api_key)
            dollar = [float(x["value"]) for x in reversed(dollar_obs) if x.get("value") not in {None, "."}]
            ten_y = [float(x["value"]) for x in reversed(yield_obs) if x.get("value") not in {None, "."}]
            out.update({
                "available": bool(dollar or ten_y),
                "provider": "FRED",
                "dollar_index": dollar[-1] if dollar else None,
                "dollar_change_window_pct": _pct_change(dollar),
                "us10y_yield": ten_y[-1] if ten_y else None,
                "us10y_change_window_pct": _pct_change(ten_y),
            })
        except Exception as exc:
            out["errors"].append(f"fred: {exc}")

    if not out["available"]:
        try:
            dxy = _yahoo_chart("DX-Y.NYB")
            tnx = _yahoo_chart("%5ETNX")
            out.update({
                "available": bool(dxy or tnx),
                "provider": "Yahoo chart fallback",
                "dollar_index": dxy[-1] if dxy else None,
                "dollar_change_window_pct": _pct_change(dxy[-6:]),
                "us10y_yield": tnx[-1] if tnx else None,
                "us10y_change_window_pct": _pct_change(tnx[-6:]),
            })
        except Exception as exc:
            out["errors"].append(f"public_fallback: {exc}")

    out["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return out
