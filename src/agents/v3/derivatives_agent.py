from __future__ import annotations

from src.agents.v3.expert_common import maybe_llm_interpret
from src.tools.research.derivatives_tool import fetch_btc_derivatives


def _fallback(raw: dict, price_change_1d: float | None = None) -> dict:
    if not raw.get("available"):
        return {
            "available": False, "regime": "UNAVAILABLE", "score": 0.0, "confidence": 0.15,
            "summary": "Derivatives data unavailable.", "evidence": [], "risks": raw.get("errors", []), "raw": raw,
            "interpretation_source": "fallback",
        }

    oi = raw.get("open_interest_change_24h_pct")
    funding = raw.get("funding_rate")
    gls = raw.get("global_long_short_ratio")
    taker = raw.get("taker_buy_sell_ratio")
    p = price_change_1d or 0.0
    score = 0.0
    evidence, risks = [], []

    if funding is not None:
        evidence.append(f"Funding {funding * 100:.4f}%")
        if funding > 0.0005:
            score -= 10
            risks.append("Positive funding indicates long-side crowding.")
        elif funding < 0:
            score += 8

    if oi is not None:
        evidence.append(f"Open-interest value change 24h {oi:+.2f}%")
        if p > 0 and oi < -1:
            score += 22
            regime = "SHORT_SQUEEZE"
        elif p > 0 and oi > 4:
            score += 4
            risks.append("Price and OI rising together can indicate leveraged longs.")
            regime = "LEVERAGED_BULL"
        elif p < 0 and oi < -2:
            score -= 18
            regime = "LONG_FLUSH"
        elif p < 0 and oi > 3:
            score -= 20
            regime = "BEARISH_LEVERAGE"
        else:
            regime = "NEUTRAL"
    else:
        regime = "NEUTRAL"

    if gls is not None:
        evidence.append(f"Global long/short ratio {gls:.2f}")
        if gls > 1.8:
            score -= 10
            risks.append("Long/short ratio is crowded to the long side.")
        elif gls < 0.8:
            score += 8

    if taker is not None:
        evidence.append(f"Taker buy/sell ratio {taker:.2f}")
        score += max(-10, min(10, (taker - 1.0) * 30))

    if regime == "NEUTRAL" and p > 0 and (oi is None or oi <= 3) and (funding is None or funding < 0.0005):
        regime = "HEALTHY_BULL"
        score += 12

    score = max(-100.0, min(100.0, score))
    return {
        "available": True,
        "regime": regime,
        "score": round(score, 1),
        "confidence": 0.72 if oi is not None and funding is not None else 0.55,
        "summary": f"Derivatives regime classified as {regime}.",
        "evidence": evidence,
        "risks": risks,
        "raw": raw,
        "interpretation_source": "fallback",
    }


def run_derivatives_agent(core_context: dict, raw: dict | None = None) -> dict:
    raw = raw or fetch_btc_derivatives()
    price_change = core_context.get("latest", {}).get("return_3d")
    # Use 3D move as a stable proxy when no 24h spot feature is available.
    fallback = _fallback(raw, price_change)
    return maybe_llm_interpret("derivatives", {"core": core_context, "tool": raw}, fallback)
