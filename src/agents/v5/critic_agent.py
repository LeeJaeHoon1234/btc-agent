from __future__ import annotations

from src.agents.llm_client import call_json_agent, llm_available


def critique_v5(*, analysis: dict, facts: list[dict], forecasts: dict, events: list[dict], data_health: dict, council: dict) -> dict:
    fact_ids = {str(x.get("id")) for x in facts if x.get("id")}
    issues: list[str] = []
    for h, item in (analysis.get("horizons") or {}).items():
        ids = item.get("key_signal_ids") or []
        if any(str(x) not in fact_ids for x in ids): issues.append(f"{h}: invalid fact citation")
        f = forecasts.get(h) or {}
        p = f.get("probability_up_pct"); exp = f.get("expected_return_pct"); stance = item.get("stance")
        if p is not None and exp is not None:
            if stance == "POSITIVE" and float(p) < 45 and float(exp) < 0: issues.append(f"{h}: positive stance conflicts with forecast distribution")
            if stance == "NEGATIVE" and float(p) > 55 and float(exp) > 0: issues.append(f"{h}: negative stance conflicts with forecast distribution")
    unavailable = [k for k,v in data_health.items() if isinstance(v,dict) and v.get("status") != "ok"]
    fallback = {"passed": not issues, "severity": "medium" if issues else "low", "issues": issues, "warnings": [f"Unavailable: {', '.join(unavailable)}"] if unavailable else [], "source": "v5_rule_critic"}
    if not llm_available(): return fallback
    instruction = """
You are BitScope V5's independent critic. Stress-test the horizon analysis using only raw facts, forecast distributions, events, data health, and council dissent.
Look for unsupported citations, time-horizon confusion, forecast contradiction, ignored tail risk, overconfidence, or treating missing data as present.
Do not create new market facts. JSON only: {"passed":true,"severity":"low|medium|high","issues":[],"warnings":[]}
"""
    try:
        r = call_json_agent(instruction, {"analysis":analysis,"raw_facts":facts,"forecasts":forecasts,"events":events,"data_health":data_health,"council":council})
        llm_issues=[str(x)[:240] for x in r.get("issues",[])][:6]
        return {"passed": bool(r.get("passed", not (issues or llm_issues))) and not issues, "severity": str(r.get("severity", fallback["severity"])), "issues": (issues+llm_issues)[:8], "warnings":[str(x)[:240] for x in r.get("warnings",fallback["warnings"])][:6], "source":"v5_llm_critic"}
    except Exception:
        return fallback
