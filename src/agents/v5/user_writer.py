from __future__ import annotations

from src.agents.llm_client import call_json_agent, llm_available


def _fallback(*, horizons: dict, forecasts: dict, portfolio: dict, risk_governor: dict, market_state: dict, language: str) -> dict:
    now = horizons.get("NOW", {}); f1w = forecasts.get("1W", {})
    target = portfolio.get("target_exposure_pct"); delta = portfolio.get("recommended_change_pct")
    if language == "en":
        headline = now.get("headline") or "The market is being reassessed in real time."
        if delta is None: action = f"Target exposure: {target:.0f}%" if target is not None else "Hold"
        else: action = f"Increase {delta:.0f} pp" if delta > 1 else f"Reduce {abs(delta):.0f} pp" if delta < -1 else "Hold"
        summary = f"1-week expected return {float(f1w.get('expected_return_pct',0)):+.1f}% with {float(f1w.get('probability_up_pct',50)):.0f}% probability of finishing higher. Risk governor cap: {float(risk_governor.get('max_allowed_exposure_pct',100)):.0f}%."
        hold_action = "Consider reducing" if portfolio.get("action") == "REDUCE" else "Hold"
        actions={"hold":hold_action,"add":action if delta is None or delta>=0 else "Wait","take_profit":"Reduce only if target exposure is below current exposure"}
    else:
        headline = now.get("headline") or "실시간 시장 구조를 다시 평가하고 있습니다."
        if delta is None: action = f"목표 비중 {target:.0f}%" if target is not None else "유지"
        else: action = f"{delta:.0f}%p 늘리기" if delta > 1 else f"{abs(delta):.0f}%p 줄이기" if delta < -1 else "유지"
        summary = f"1주 기대수익 {float(f1w.get('expected_return_pct',0)):+.1f}%, 상승확률 {float(f1w.get('probability_up_pct',50)):.0f}%입니다. Risk Governor 상한은 {float(risk_governor.get('max_allowed_exposure_pct',100)):.0f}%입니다."
        actions={"hold":"리스크 상한 안에서 유지","add":action if delta is None or delta>=0 else "기다림","take_profit":"현재 비중이 목표보다 높을 때만 축소 검토"}
    market_label = str((market_state or {}).get("regime") or "unknown").replace("_", " ")
    disagreement = float((risk_governor or {}).get("max_allowed_exposure_pct", 100) or 100)
    levels = (portfolio or {}).get("levels") or {}
    if language == "en":
        why = [
            f"1W distribution: {float(f1w.get('probability_up_pct',50)):.0f}% up probability and {float(f1w.get('expected_return_pct',0)):+.1f}% expected return.",
            f"Current market state: {market_label}.",
        ]
        watch = list(risk_governor.get("reasons", [])[:2])
        if levels.get("invalidation_anchor"):
            watch.append(f"Reassess the scenario around the invalidation anchor near ₩{float(levels['invalidation_anchor']):,.0f}.")
    else:
        why = [
            f"1주 분포는 상승확률 {float(f1w.get('probability_up_pct',50)):.0f}%, 기대수익 {float(f1w.get('expected_return_pct',0)):+.1f}%입니다.",
            f"현재 시장 국면은 {market_label}입니다.",
        ]
        watch = list(risk_governor.get("reasons", [])[:2])
        if levels.get("invalidation_anchor"):
            watch.append(f"약 ₩{float(levels['invalidation_anchor']):,.0f} 무효화 기준 부근에서는 시나리오를 다시 봅니다.")
    return {"headline":headline,"summary":summary,"decision":action,"actions":actions,"why":why[:3],"watch":watch[:3],"source":"v5_fallback","language":language}


def write_user_view_v5(*, horizons: dict, forecasts: dict, portfolio: dict, risk_governor: dict, meta_decision: dict, market_state: dict, council: dict, critic: dict, language: str="ko") -> dict:
    language="en" if language=="en" else "ko"
    fallback=_fallback(horizons=horizons,forecasts=forecasts,portfolio=portfolio,risk_governor=risk_governor,market_state=market_state,language=language)
    if not llm_available(): return fallback
    instruction="""
You are BitScope V5's final plain-language writer. Do not perform new analysis and do not change any number.
Explain what is happening, what the forecast distribution says, the approved target exposure, and the strongest uncertainty in language a non-expert understands quickly.
The Risk Governor is authoritative. Never recommend exposure above its approved amount. Avoid internal engineering jargon.
JSON only: {"headline":"...","summary":"max 2 sentences","decision":"short action","actions":{"hold":"...","add":"...","take_profit":"..."},"why":["max3"],"watch":["max3"]}
"""
    try:
        r=call_json_agent(instruction,{"horizons":horizons,"forecasts":forecasts,"portfolio":portfolio,"risk_governor":risk_governor,"meta_decision":meta_decision,"market_state":market_state,"council":council,"critic":critic,"language":language})
        actions=r.get("actions",{}) if isinstance(r.get("actions"),dict) else {}
        return {"headline":str(r.get("headline",fallback["headline"]))[:180],"summary":str(r.get("summary",fallback["summary"]))[:420],"decision":str(r.get("decision",fallback["decision"]))[:120],"actions":{"hold":str(actions.get("hold",fallback["actions"]["hold"]))[:100],"add":str(actions.get("add",fallback["actions"]["add"]))[:100],"take_profit":str(actions.get("take_profit",fallback["actions"]["take_profit"]))[:100]},"why":[str(x)[:180] for x in r.get("why",[])][:3],"watch":[str(x)[:180] for x in r.get("watch",[])][:3],"source":"v5_llm_writer","language":language}
    except Exception:
        return fallback
