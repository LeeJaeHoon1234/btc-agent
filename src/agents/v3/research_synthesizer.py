from __future__ import annotations

from src.agents.llm_client import call_json_agent, llm_available

WEIGHTS = {"technical": 0.20, "derivatives": 0.25, "macro": 0.20, "news": 0.15, "historical": 0.20}


def _fallback(experts: dict) -> dict:
    weighted = 0.0
    weight_sum = 0.0
    bullish, bearish, unknowns = [], [], []
    for name, result in experts.items():
        if name == "risk":
            continue
        if not isinstance(result, dict) or not result.get("available", True):
            unknowns.append(f"{name}: unavailable")
            continue
        weight = WEIGHTS.get(name, 0.1) * max(0.2, float(result.get("confidence", 0.5)))
        score = float(result.get("score", 0))
        weighted += score * weight
        weight_sum += weight
        item = f"{name}: {result.get('summary', '')}"
        if score >= 8:
            bullish.append(item)
        elif score <= -8:
            bearish.append(item)
    score = weighted / weight_sum if weight_sum else 0.0
    if score >= 15:
        stance = "BULLISH"
    elif score <= -15:
        stance = "BEARISH"
    else:
        stance = "MIXED"
    return {
        "stance": stance,
        "score": round(score, 1),
        "confidence": round(min(0.85, 0.45 + weight_sum / 2.5), 2),
        "market_story": f"Cross-domain research is {stance.lower()} with bounded score {score:.1f}.",
        "bullish_factors": bullish[:6],
        "bearish_factors": bearish[:6],
        "unknowns": unknowns[:6],
        "source": "fallback",
    }


def synthesize_research(question: str, plan: dict, experts: dict) -> dict:
    fallback = _fallback(experts)
    if not llm_available():
        return fallback
    instruction = """
You are the senior BTC research synthesizer. Multiple specialist agents have already gathered evidence.
Synthesize; do not redo their tool work. Separate facts from interpretation. Missing data must stay missing.
Do not promise returns or use certainty language.
Return JSON only:
{
  "stance": "BULLISH|MIXED|BEARISH",
  "score": -100 to 100,
  "confidence": 0.0 to 1.0,
  "market_story": "concise explanation of what is driving the market",
  "bullish_factors": ["..."],
  "bearish_factors": ["..."],
  "unknowns": ["..."]
}
"""
    try:
        result = call_json_agent(instruction, {"question": question, "plan": plan, "experts": experts})
        score = max(-100, min(100, float(result.get("score", fallback["score"]))))
        confidence = max(0, min(1, float(result.get("confidence", fallback["confidence"]))))
        return {
            "stance": str(result.get("stance", fallback["stance"])),
            "score": score,
            "confidence": confidence,
            "market_story": str(result.get("market_story", fallback["market_story"])),
            "bullish_factors": list(result.get("bullish_factors", fallback["bullish_factors"]))[:8],
            "bearish_factors": list(result.get("bearish_factors", fallback["bearish_factors"]))[:8],
            "unknowns": list(result.get("unknowns", fallback["unknowns"]))[:8],
            "source": "llm",
        }
    except Exception:
        return fallback
