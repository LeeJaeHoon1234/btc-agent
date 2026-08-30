from __future__ import annotations

from src.agents.v3.expert_common import maybe_llm_interpret
from src.retrieval.historical_rag import retrieve_historical_cases


def run_historical_agent(df, core_context: dict) -> dict:
    raw = retrieve_historical_cases(df)
    if not raw.get("available"):
        return {
            "available": False, "score": 0.0, "confidence": 0.2, "summary": raw.get("message", "Historical retrieval unavailable."),
            "cases": [], "evidence": [], "risks": ["Historical analogs are unavailable."], "raw": raw,
            "interpretation_source": "fallback",
        }
    median30 = float(raw.get("median_forward_30d_pct", 0))
    dispersion = float(raw.get("dispersion_30d_pct", 0))
    score = max(-60.0, min(60.0, median30 * 2.2))
    confidence = max(0.25, min(0.8, 0.72 - dispersion / 100))
    fallback = {
        "available": True,
        "score": round(score, 1),
        "confidence": round(confidence, 2),
        "summary": f"Historical analog median 30D return is {median30:+.2f}% with {dispersion:.2f}% dispersion.",
        "cases": raw.get("cases", []),
        "evidence": [f"{c['date']}: 7D {c['forward_7d_pct']:+.1f}%, 30D {c['forward_30d_pct']:+.1f}%" for c in raw.get("cases", [])],
        "risks": ["Similarity is descriptive and does not imply the current market will repeat history."],
        "raw": raw,
        "interpretation_source": "fallback",
    }
    interpreted = maybe_llm_interpret("historical", {"core": core_context, "retrieval": raw}, fallback)
    interpreted["cases"] = raw.get("cases", [])
    return interpreted
