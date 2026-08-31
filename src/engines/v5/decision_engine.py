from __future__ import annotations

import math


def _utility(item: dict) -> float:
    if not item or not item.get("available"):
        return 0.0
    exp = float(item.get("expected_return_pct", 0.0) or 0.0)
    q10 = abs(float(item.get("q10_return_pct", 0.0) or 0.0))
    disp = abs(float(item.get("dispersion_pct", 0.0) or 0.0))
    conf = float(item.get("confidence", 0.4) or 0.4)
    downside = max(1.0, q10, disp * 0.8)
    return (exp / downside) * conf


def build_base_decision(*, forecasts: dict, council: dict, market_state: dict) -> dict:
    u_now = _utility(forecasts.get("NOW", {})); u_1w = _utility(forecasts.get("1W", {})); u_1m = _utility(forecasts.get("1M", {})); u_1y = _utility(forecasts.get("1Y", {}))
    utility = 0.10 * u_now + 0.38 * u_1w + 0.42 * u_1m + 0.10 * u_1y
    agents = (council or {}).get("agents", {})
    bullish = sum(1 for k, v in agents.items() if k != "risk" and v.get("stance") == "BULLISH")
    bearish = sum(1 for k, v in agents.items() if k != "risk" and v.get("stance") == "BEARISH")
    council_shift = (bullish - bearish) * 3.0
    risk_pressure = float((agents.get("risk") or {}).get("risk_pressure", 0.0) or 0.0)
    target = 50.0 + utility * 38.0 + council_shift - risk_pressure * 0.28
    acute = str((market_state or {}).get("acute_state") or "normal")
    if acute in {"bearish_leverage", "volatility_shock_down"}: target -= 10
    elif acute in {"long_flush", "short_squeeze"}: target += 3
    target = max(0.0, min(100.0, target))

    if target >= 62: action = "INCREASE"
    elif target <= 35: action = "REDUCE"
    else: action = "HOLD"
    return {
        "action": action,
        "desired_exposure_pct": round(target, 1),
        "utility": round(utility, 4),
        "council_shift_pct": round(council_shift, 1),
        "risk_pressure": round(risk_pressure, 1),
        "components": {"NOW": round(u_now, 4), "1W": round(u_1w, 4), "1M": round(u_1m, 4), "1Y": round(u_1y, 4)},
        "source": "quantitative_decision_engine",
    }
