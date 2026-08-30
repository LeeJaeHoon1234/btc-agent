from __future__ import annotations

from src.agents.v3.expert_common import maybe_llm_interpret
from src.tools.research.macro_tool import fetch_macro_snapshot


def _fallback(raw: dict) -> dict:
    if not raw.get("available"):
        return {
            "available": False, "regime": "UNAVAILABLE", "score": 0.0, "confidence": 0.15,
            "summary": "Macro data unavailable; it is not treated as neutral evidence.",
            "evidence": [], "risks": raw.get("errors", []), "raw": raw, "interpretation_source": "fallback",
        }
    score = 0.0
    evidence, risks = [], []
    dxy = raw.get("dollar_change_window_pct")
    y10 = raw.get("us10y_change_window_pct")
    if dxy is not None:
        evidence.append(f"Dollar index window change {dxy:+.2f}%")
        score += max(-30, min(30, -dxy * 15))
    if y10 is not None:
        evidence.append(f"US 10Y yield window change {y10:+.2f}%")
        score += max(-25, min(25, -y10 * 8))
    if score >= 15:
        regime = "RISK_ON_TAILWIND"
    elif score <= -15:
        regime = "RISK_OFF_HEADWIND"
    else:
        regime = "NEUTRAL"
    return {
        "available": True, "regime": regime, "score": round(score, 1), "confidence": 0.62,
        "summary": f"Macro backdrop classified as {regime}.", "evidence": evidence, "risks": risks,
        "raw": raw, "interpretation_source": "fallback",
    }


def run_macro_agent(core_context: dict, raw: dict | None = None) -> dict:
    raw = raw or fetch_macro_snapshot()
    fallback = _fallback(raw)
    return maybe_llm_interpret("macro", {"core": core_context, "tool": raw}, fallback)
