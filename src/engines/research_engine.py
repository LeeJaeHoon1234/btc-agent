from __future__ import annotations


def apply_research_adjustment(entry: dict, exit_signal: dict, research: dict) -> dict:
    """Bound research influence so external/LLM evidence cannot overwhelm the core engine."""
    score = float(research.get("score", 0))
    confidence = float(research.get("confidence", 0.5))
    delta = max(-8.0, min(8.0, score * confidence * 0.10))
    adjusted_entry = max(0.0, min(100.0, float(entry.get("score", 50)) + delta))
    # Negative research modestly increases exit pressure; positive research modestly reduces it.
    adjusted_exit = max(0.0, min(100.0, float(exit_signal.get("score", 0)) - delta * 0.55))
    return {
        "entry_delta": round(delta, 2),
        "adjusted_entry_score": round(adjusted_entry, 2),
        "adjusted_exit_score": round(adjusted_exit, 2),
        "bounded": True,
        "note": "Research can move the core score by at most ±8 points.",
    }
