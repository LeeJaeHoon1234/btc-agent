from __future__ import annotations


def apply_risk_governor(*, proposed_exposure_pct: float, forecasts: dict, market_state: dict, data_health: dict, events: list[dict], council: dict) -> dict:
    """Non-LLM hard safety layer. It can cap or block exposure but never increase it."""
    cap = 100.0
    reasons: list[str] = []
    critical = ["price", "intraday"]
    missing_critical = [k for k in critical if (data_health.get(k) or {}).get("status") != "ok"]
    if missing_critical:
        cap = 0.0; reasons.append(f"critical data unavailable: {', '.join(missing_critical)}")

    unavailable = [k for k, v in (data_health or {}).items() if isinstance(v, dict) and v.get("status") != "ok"]
    if len(unavailable) >= 4:
        cap = min(cap, 35.0); reasons.append("too many evidence sources unavailable")

    q10w = (forecasts.get("1W") or {}).get("q10_return_pct")
    q10m = (forecasts.get("1M") or {}).get("q10_return_pct")
    if q10w is not None and float(q10w) <= -15:
        cap = min(cap, 35.0); reasons.append("1W historical-neighbor downside tail is severe")
    elif q10w is not None and float(q10w) <= -10:
        cap = min(cap, 55.0); reasons.append("1W downside tail is elevated")
    if q10m is not None and float(q10m) <= -25:
        cap = min(cap, 45.0); reasons.append("1M downside tail is severe")

    acute = str((market_state or {}).get("acute_state") or "normal")
    if acute in {"bearish_leverage", "volatility_shock_down"}:
        cap = min(cap, 30.0); reasons.append(f"acute state: {acute}")
    elif acute == "long_flush":
        cap = min(cap, 65.0); reasons.append("long flush detected; recovery is not assumed")

    adverse_events = [e for e in events or [] if e.get("direction") == -1 or e.get("kind") in {"rejection"}]
    max_adverse_event = max([float(e.get("severity", 0) or 0) for e in adverse_events] or [0.0])
    if max_adverse_event >= 5:
        cap = min(cap, 20.0); reasons.append("severity-5 adverse market event")
    elif max_adverse_event >= 4:
        cap = min(cap, 45.0); reasons.append("severity-4 adverse market event")

    disagreement = float((council or {}).get("disagreement", 0.0) or 0.0)
    if disagreement >= 0.65:
        cap = min(cap, 60.0); reasons.append("high agent disagreement")

    approved = max(0.0, min(float(proposed_exposure_pct), cap))
    return {
        "proposed_exposure_pct": round(float(proposed_exposure_pct), 1),
        "max_allowed_exposure_pct": round(cap, 1),
        "approved_exposure_pct": round(approved, 1),
        "capped": approved + 1e-9 < float(proposed_exposure_pct),
        "blocked": cap <= 0,
        "reasons": reasons,
        "max_single_change_pct": 20.0 if cap >= 50 else 10.0,
        "source": "hard_risk_governor",
    }
