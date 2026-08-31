from __future__ import annotations

from typing import Any


def split_facts_and_priors(signals: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Split auditable market facts from deterministic interpretation priors.

    V4 mixed factual values with direction/strength hints in the same object. V5 keeps
    them separate so autonomous analysts can inspect raw facts without anchoring on
    hand-written thresholds. Priors remain available only for deterministic fallbacks.
    """
    facts: list[dict[str, Any]] = []
    priors: dict[str, dict[str, Any]] = {}
    for raw in signals or []:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        sid = str(raw["id"])
        facts.append({
            "id": sid,
            "domain": raw.get("domain"),
            "horizons": list(raw.get("horizons") or []),
            "fact": raw.get("fact"),
            "simple": raw.get("simple"),
            "value": raw.get("value"),
            "freshness": raw.get("freshness"),
        })
        priors[sid] = {
            "direction": int(raw.get("direction", 0) or 0),
            "strength": float(raw.get("strength", 0.0) or 0.0),
            "source": "deterministic_fallback_only",
        }
    return facts, priors
