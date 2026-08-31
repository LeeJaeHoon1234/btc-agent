from __future__ import annotations

from src.agents.llm_client import call_json_agent, llm_available

ALLOWED = {"INCREASE", "HOLD", "REDUCE", "AVOID"}


def run_meta_decision(*, base_decision: dict, facts: list[dict], forecasts: dict, council: dict, market_state: dict, events: list[dict], language: str = "ko") -> dict:
    """LLM may challenge the quantitative target, but only inside a narrow auditable band.

    This is intentional: language reasoning gets autonomy over interpretation, not unlimited
    authority over portfolio math.
    """
    fallback = dict(base_decision) | {"reason": "Quantitative target retained.", "dissent": "", "source": "quant_fallback"}
    if not llm_available():
        return fallback
    base = float(base_decision.get("desired_exposure_pct", 50.0))
    instruction = """
You are BitScope V5's Meta Decision Agent. Challenge the quantitative decision using only the supplied raw facts, forecasts, independent council views, market state and events.
Do not invent numbers. Do not simply majority-vote the council. Forecast distributions are the numerical anchor.
You may move desired exposure by at most 10 percentage points from base_target. If uncertainty is high, prefer HOLD or lower exposure.
Return JSON only:
{"action":"INCREASE|HOLD|REDUCE|AVOID","desired_exposure_pct":0,"reason":"max 3 sentences","dissent":"strongest argument against your decision"}
"""
    try:
        result = call_json_agent(instruction, {
            "base_target": base, "base_decision": base_decision, "raw_facts": facts,
            "forecasts": forecasts, "council": council, "market_state": market_state, "events": (events or [])[:5],
            "language": language,
        })
        requested = float(result.get("desired_exposure_pct", base))
        bounded = max(0.0, min(100.0, max(base - 10.0, min(base + 10.0, requested))))
        action = str(result.get("action", fallback["action"])).upper()
        if action not in ALLOWED: action = fallback["action"]
        return {
            **base_decision,
            "action": action,
            "desired_exposure_pct": round(bounded, 1),
            "llm_requested_exposure_pct": round(requested, 1),
            "reason": str(result.get("reason", ""))[:600],
            "dissent": str(result.get("dissent", ""))[:360],
            "adjustment_from_quant_pct": round(bounded - base, 1),
            "source": "llm_bounded_meta_agent",
        }
    except Exception as exc:
        return fallback | {"meta_error": str(exc)}
