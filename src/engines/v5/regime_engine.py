from __future__ import annotations

import math


def _f(value, default=0.0):
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def detect_market_state(*, latest: dict, live: dict, derivatives: dict | None = None, base_regime: dict | None = None) -> dict:
    """Two-speed regime detector: structural daily trend + acute intraday/leverage state."""
    metrics = (live or {}).get("metrics") or {}
    derivatives = derivatives or {}
    slow = str((base_regime or {}).get("regime") or "unknown")
    r1 = _f(metrics.get("return_1h_pct")); r4 = _f(metrics.get("return_4h_pct")); r24 = _f(metrics.get("return_24h_pct"))
    rebound = _f(metrics.get("rebound_from_24h_low_pct")); volz = _f(metrics.get("volume_zscore")); atr = _f(metrics.get("atr14_pct"))
    oi = _f(derivatives.get("open_interest_change_24h_pct")); funding = _f(derivatives.get("funding_rate")); taker = _f(derivatives.get("taker_buy_sell_ratio"), 1.0)
    dd = _f(latest.get("drawdown_from_ath_pct")); ma200 = _f(latest.get("ma200_gap_pct")); slope200 = _f(latest.get("ma200_slope_20d"))

    acute = "normal"
    reasons: list[str] = []
    if abs(r1) >= 3 or abs(r4) >= 6 or atr >= 3.5:
        shock_direction = r1 if abs(r1) >= abs(r4) / 2 else r4
        acute = "volatility_shock_up" if shock_direction > 0 else "volatility_shock_down"
        reasons.append("short-horizon upside volatility shock" if shock_direction > 0 else "short-horizon downside volatility shock")
    if r4 <= -4 and oi <= -5 and rebound >= 1.5:
        acute = "long_flush"; reasons.append("sharp drop with open-interest contraction and rebound")
    elif r4 >= 3 and oi >= 7 and funding >= 0.00035:
        acute = "leveraged_rally"; reasons.append("price, leverage and funding rising together")
    elif r4 >= 2 and oi <= -3:
        acute = "short_squeeze"; reasons.append("price rising while open interest contracts")
    elif r4 <= -3 and oi >= 5:
        acute = "bearish_leverage"; reasons.append("price falling while leverage expands")
    elif r1 > 0.5 and r4 < -1.0:
        acute = "rebound_attempt"; reasons.append("short rebound inside a weaker multi-hour move")

    if slow == "bull_trend":
        regime = "strong_bull"
        if acute == "long_flush": regime = "bull_flush_recovery"
        elif acute in {"volatility_shock_down", "bearish_leverage"}: regime = "bull_under_stress"
        elif acute == "leveraged_rally": regime = "leveraged_bull"
        elif r24 < -2 or ma200 < 0: regime = "bull_pullback"
    elif slow == "bull_transition":
        regime = "recovery" if r4 >= 0 else "bull_pullback"
        if acute == "long_flush": regime = "flush_recovery"
        elif acute == "leveraged_rally": regime = "leveraged_recovery"
    elif slow == "bear_trend":
        regime = "bear_trend"
        if acute in {"short_squeeze", "rebound_attempt"}: regime = "bear_rally"
        elif r4 <= -4 and dd <= -25: regime = "capitulation"
    elif slow == "bear_transition":
        regime = "distribution"
        if acute in {"short_squeeze", "rebound_attempt"}: regime = "bear_rally"
        elif acute == "bearish_leverage": regime = "bear_acceleration"
    else:
        regime = "range"
        if acute in {"volatility_shock_up", "volatility_shock_down"}: regime = "range_break_shock"
        elif acute == "long_flush": regime = "range_flush"

    confidence = 0.58
    confidence += 0.08 if slow != "unknown" else -0.08
    confidence += 0.06 if derivatives.get("available") else -0.04
    confidence += 0.05 if (live or {}).get("available") else -0.10
    confidence = max(0.30, min(0.88, confidence))
    return {
        "regime": regime,
        "structural_regime": slow,
        "acute_state": acute,
        "confidence": round(confidence, 2),
        "reasons": reasons[:5],
        "features": {
            "return_1h_pct": r1, "return_4h_pct": r4, "return_24h_pct": r24,
            "rebound_from_day_low_pct": rebound, "volume_zscore": volz, "atr_pct": atr,
            "oi_change_24h_pct": oi, "funding_rate": funding, "derivatives_taker_ratio": taker,
            "ma200_gap_pct": ma200, "ma200_slope_20d": slope200, "drawdown_from_ath_pct": dd,
        },
        "method": "two_speed_rule_state_detector",
    }
