from __future__ import annotations

from copy import deepcopy

from src.agents.llm_client import call_json_agent, llm_available

HORIZONS = ("NOW", "TODAY", "1W", "1M", "1Y")
ALLOWED_STANCES = {"POSITIVE", "NEUTRAL", "CAUTION", "NEGATIVE"}
DOMAIN_PRIORITY = {
    "NOW": ["price", "derivatives", "technical", "news"],
    "TODAY": ["price", "derivatives", "technical", "news", "flow"],
    "1W": ["derivatives", "technical", "flow", "macro", "news", "model"],
    "1M": ["flow", "macro", "technical", "model", "onchain", "sentiment"],
    "1Y": ["macro", "flow", "onchain", "model", "technical"],
}


def _fallback_view(horizon: str, facts: list[dict], forecasts: dict, market_state: dict, language: str) -> dict:
    f = forecasts.get(horizon) or {}
    p = f.get("probability_up_pct")
    exp = f.get("expected_return_pct")
    q10 = f.get("q10_return_pct")
    conf = float(f.get("confidence", 0.35) or 0.35)
    if not f.get("available"):
        stance = "NEUTRAL"
    elif p is not None and exp is not None and float(p) >= 60 and float(exp) > 0:
        stance = "POSITIVE"
    elif p is not None and exp is not None and float(p) <= 40 and float(exp) < 0:
        stance = "NEGATIVE"
    elif q10 is not None and ((horizon in {"NOW", "TODAY"} and float(q10) <= -3) or (horizon == "1W" and float(q10) <= -10) or (horizon == "1M" and float(q10) <= -18)):
        stance = "CAUTION"
    else:
        stance = "NEUTRAL"

    priorities = DOMAIN_PRIORITY[horizon]
    relevant = [x for x in facts if horizon in (x.get("horizons") or [])]
    relevant.sort(key=lambda x: priorities.index(x.get("domain")) if x.get("domain") in priorities else 99)
    ids = [str(x.get("id")) for x in relevant[:5] if x.get("id")]
    if language == "en":
        headline = {
            "POSITIVE": "The probability distribution leans constructive.",
            "NEGATIVE": "The probability distribution leans to the downside.",
            "CAUTION": "Downside dispersion is too wide for a strong directional call.",
            "NEUTRAL": "The distribution is mixed rather than strongly directional.",
        }[stance]
        summary = f"Expected return {float(exp):+.1f}% with {float(p):.0f}% probability of finishing higher." if p is not None and exp is not None else "There is not enough validated data for a strong forecast."
    else:
        headline = {
            "POSITIVE": "확률분포는 상승 쪽이 조금 더 유리합니다.",
            "NEGATIVE": "확률분포는 하락 쪽으로 기울어 있습니다.",
            "CAUTION": "하방 범위가 넓어 방향을 세게 잡기 어렵습니다.",
            "NEUTRAL": "한쪽으로 강하게 기운 분포는 아닙니다.",
        }[stance]
        summary = f"기대수익 {float(exp):+.1f}%, 상승확률 {float(p):.0f}%입니다." if p is not None and exp is not None else "검증된 데이터가 부족해 강한 전망을 내기 어렵습니다."
    if language == "en":
        good = []
        risks = []
        if p is not None and float(p) >= 55:
            good.append(f"The calibrated probability of finishing higher is {float(p):.0f}%.")
        if exp is not None and float(exp) > 0:
            good.append(f"The distribution's expected return is {float(exp):+.1f}%.")
        if q10 is not None and float(q10) < 0:
            risks.append(f"The lower 10% scenario reaches about {float(q10):+.1f}%.")
        if conf < 0.6:
            risks.append(f"Distribution confidence is only {conf*100:.0f}%, so the estimate should stay provisional.")
    else:
        good = []
        risks = []
        if p is not None and float(p) >= 55:
            good.append(f"교정된 상승확률은 {float(p):.0f}%입니다.")
        if exp is not None and float(exp) > 0:
            good.append(f"분포상 기대수익은 {float(exp):+.1f}%입니다.")
        if q10 is not None and float(q10) < 0:
            risks.append(f"하단 10% 시나리오는 약 {float(q10):+.1f}%까지 열려 있습니다.")
        if conf < 0.6:
            risks.append(f"분포 신뢰도는 {conf*100:.0f}% 수준이라 잠정 판단으로 보는 게 맞습니다.")
    return {
        "horizon": horizon, "stance": stance, "confidence": round(conf, 3), "headline": headline,
        "summary": summary, "key_signal_ids": ids, "good": good[:2], "risks": risks[:2], "source": "v5_forecast_fallback",
    }


def _validate(result: dict, fallbacks: dict, valid_ids: set[str]) -> dict:
    out = deepcopy(fallbacks)
    raw = result.get("horizons", {}) if isinstance(result, dict) else {}
    for h in HORIZONS:
        c = raw.get(h, {}) if isinstance(raw, dict) else {}
        if not isinstance(c, dict):
            continue
        stance = str(c.get("stance", out[h]["stance"])).upper()
        if stance not in ALLOWED_STANCES: stance = out[h]["stance"]
        ids = [str(x) for x in c.get("key_signal_ids", []) if str(x) in valid_ids][:5] or out[h]["key_signal_ids"]
        try: confidence = max(0.2, min(0.90, float(c.get("confidence", out[h]["confidence"]))))
        except (TypeError, ValueError): confidence = out[h]["confidence"]
        out[h].update({
            "stance": stance, "confidence": confidence,
            "headline": str(c.get("headline", out[h]["headline"]))[:180],
            "summary": str(c.get("summary", out[h]["summary"]))[:420],
            "key_signal_ids": ids,
            "good": [str(x)[:180] for x in c.get("good", [])][:2],
            "risks": [str(x)[:180] for x in c.get("risks", [])][:2],
            "source": "v5_llm_raw_facts",
        })
    gv = result.get("global_view", {}) if isinstance(result, dict) else {}
    return {"horizons": out, "global_view": {k: str(gv.get(k, ""))[:300] for k in ["what_changed", "most_important", "conflict"]}, "source": "v5_llm_raw_facts"}


def analyze_horizons_v5(*, facts: list[dict], forecasts: dict, market_state: dict, events: list[dict], data_health: dict,
                        council: dict, memory: dict | None = None, language: str = "ko") -> dict:
    language = "en" if language == "en" else "ko"
    fallbacks = {h: _fallback_view(h, facts, forecasts, market_state, language) for h in HORIZONS}
    base = {"horizons": fallbacks, "global_view": {"what_changed": "", "most_important": "", "conflict": ""}, "source": "v5_forecast_fallback"}
    if not llm_available(): return base
    instruction = """
You are BitScope V5's Horizon Analyst. The payload deliberately contains RAW FACTS without hand-written bullish/bearish direction labels.
Use the numerical forecast distributions as anchors, then interpret raw facts, current market state, events, and independent council dissent.
Never invent or alter a market number. Never infer unavailable data. Do not average council members mechanically.
NOW/TODAY/1W/1M/1Y may disagree. Cite 1-5 valid fact IDs per horizon.
Confidence should reflect uncertainty; it is not a writing-strength score. Do not exceed the forecast confidence by more than 0.10 unless multiple independent raw facts strongly agree.
Return JSON only:
{"global_view":{"what_changed":"...","most_important":"...","conflict":"..."},"horizons":{"NOW":{"stance":"POSITIVE|NEUTRAL|CAUTION|NEGATIVE","confidence":0.0,"headline":"...","summary":"...","key_signal_ids":["S_..."],"good":[],"risks":[]},"TODAY":{},"1W":{},"1M":{},"1Y":{}}}
"""
    payload = {
        "raw_facts": facts, "forecast_distributions": forecasts, "market_state": market_state,
        "events": events[:6], "data_health": data_health, "independent_agent_council": council,
        "reflection_memory_weak_prior": memory or {}, "language": language,
    }
    try:
        result = call_json_agent(instruction, payload)
        checked = _validate(result, fallbacks, {str(x.get("id")) for x in facts if x.get("id")})
        # Calibration guard: cap LLM confidence relative to numerical forecast confidence.
        for h, item in checked["horizons"].items():
            fc = float((forecasts.get(h) or {}).get("confidence", 0.35) or 0.35)
            item["confidence"] = round(min(float(item.get("confidence", fc)), min(0.90, fc + 0.10)), 3)
        return checked
    except Exception:
        return base
