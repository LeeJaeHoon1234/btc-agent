from __future__ import annotations


def build_portfolio_plan(*, current_price: float | None, current_exposure_pct: float | None, risk_governor: dict, forecasts: dict, meta_decision: dict) -> dict:
    target = float(risk_governor.get("approved_exposure_pct", 0.0) or 0.0)
    max_step = float(risk_governor.get("max_single_change_pct", 10.0) or 10.0)
    current = None if current_exposure_pct is None else max(0.0, min(100.0, float(current_exposure_pct)))
    delta = None
    next_exposure = target
    if current is not None:
        raw_delta = target - current
        delta = max(-max_step, min(max_step, raw_delta))
        next_exposure = max(0.0, min(100.0, current + delta))

    price = float(current_price) if current_price else None
    f1w = forecasts.get("1W") or {}; f1m = forecasts.get("1M") or {}; fnow = forecasts.get("NOW") or {}
    q25 = float(f1w.get("q25_return_pct", 0.0) or 0.0); q10 = float(f1w.get("q10_return_pct", -5.0) or -5.0)
    q75m = float(f1m.get("q75_return_pct", 0.0) or 0.0); q90m = float(f1m.get("q90_return_pct", 0.0) or 0.0)
    intraday_sigma = abs(float(fnow.get("dispersion_pct", 1.0) or 1.0))
    levels = {}
    if price:
        entry_low = price * (1.0 - min(0.03, intraday_sigma * 0.35 / 100.0))
        add_anchor = price * (1.0 + min(0.0, q25) * 0.45 / 100.0)
        invalidation_pct = max(-12.0, min(-3.0, q10 * 0.75))
        invalidation = price * (1.0 + invalidation_pct / 100.0)
        levels = {
            "entry_zone": [round(entry_low), round(price)],
            "add_on_weakness_anchor": round(add_anchor),
            "invalidation_anchor": round(invalidation),
            "take_profit_1": round(price * (1.0 + max(0.0, q75m) / 100.0)),
            "take_profit_2": round(price * (1.0 + max(0.0, q90m) / 100.0)),
            "level_method": "forecast_quantile_scenario_anchors",
        }

    action = "HOLD"
    if delta is not None:
        action = "INCREASE" if delta > 1 else "REDUCE" if delta < -1 else "HOLD"
    else:
        action = str(meta_decision.get("action") or "HOLD")
    return {
        "action": action,
        "current_exposure_pct": current,
        "target_exposure_pct": round(target, 1),
        "recommended_change_pct": None if delta is None else round(delta, 1),
        "next_exposure_pct": round(next_exposure, 1),
        "levels": levels,
        "note": "Position sizes are risk-budget suggestions for decision support; no exchange order is placed.",
    }
