from __future__ import annotations

from datetime import datetime, timezone
import requests

TIMEOUT = 8


def fetch_network_snapshot() -> dict:
    """Public network-health inputs. Valuation metrics such as MVRV/SOPR are intentionally not fabricated."""
    out = {
        "available": False,
        "provider": "Blockchain.com + mempool.space",
        "errors": [],
        "valuation_metrics_available": False,
        "missing_valuation_metrics": ["MVRV", "SOPR", "LTH/STH realized metrics"],
    }
    try:
        r = requests.get("https://api.blockchain.info/stats", timeout=TIMEOUT)
        r.raise_for_status()
        x = r.json()
        out.update({
            "hash_rate": x.get("hash_rate"),
            "difficulty": x.get("difficulty"),
            "minutes_between_blocks": x.get("minutes_between_blocks"),
            "n_tx": x.get("n_tx"),
            "total_fees_btc": (float(x.get("total_fees_btc", 0)) / 100000000) if x.get("total_fees_btc") is not None else None,
        })
    except Exception as exc:
        out["errors"].append(f"blockchain_stats: {type(exc).__name__}: {exc}")
    try:
        r = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=TIMEOUT)
        r.raise_for_status()
        fees = r.json()
        out["fee_fastest_sat_vb"] = fees.get("fastestFee")
        out["fee_half_hour_sat_vb"] = fees.get("halfHourFee")
        out["fee_hour_sat_vb"] = fees.get("hourFee")
    except Exception as exc:
        out["errors"].append(f"mempool_fees: {type(exc).__name__}: {exc}")
    out["available"] = any(out.get(k) is not None for k in ["hash_rate", "difficulty", "fee_fastest_sat_vb"])
    out["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return out
