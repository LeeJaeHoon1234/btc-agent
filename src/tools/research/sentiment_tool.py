from __future__ import annotations

from datetime import datetime, timezone
import requests

TIMEOUT = 8


def fetch_fear_greed(limit: int = 7) -> dict:
    out = {"available": False, "provider": "Alternative.me", "errors": []}
    try:
        r = requests.get("https://api.alternative.me/fng/", params={"limit": max(2, min(limit, 30)), "format": "json"}, timeout=TIMEOUT)
        r.raise_for_status()
        rows = r.json().get("data", [])
        values = [int(x["value"]) for x in rows if str(x.get("value", "")).isdigit()]
        latest = rows[0] if rows else {}
        out.update({
            "available": bool(values),
            "value": values[0] if values else None,
            "classification": latest.get("value_classification"),
            "change_7obs": (values[0] - values[-1]) if len(values) >= 2 else None,
            "history": [{"value": int(x["value"]), "classification": x.get("value_classification"), "timestamp": x.get("timestamp")} for x in rows if str(x.get("value", "")).isdigit()],
            "attribution": "Alternative.me Crypto Fear & Greed Index",
        })
    except Exception as exc:
        out["errors"].append(f"fear_greed: {type(exc).__name__}: {exc}")
    out["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return out
