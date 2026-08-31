from __future__ import annotations

from src.agents.llm_client import call_json_agent, llm_available


def _fallback(analysis: dict, signal_map: dict[str, dict], data_health: dict) -> dict:
    issues = []
    for h, item in (analysis.get("horizons") or {}).items():
        ids = item.get("key_signal_ids", [])
        if not ids: issues.append(f"{h}: 근거 ID가 없음")
        missing = [x for x in ids if x not in signal_map]
        if missing: issues.append(f"{h}: 존재하지 않는 근거 {missing}")
    unavailable = [k for k, v in data_health.items() if isinstance(v, dict) and v.get("status") == "unavailable"]
    return {"passed": not issues, "severity": "medium" if issues else "low", "issues": issues, "warnings": [f"데이터 없음: {', '.join(unavailable)}"] if unavailable else [], "source": "rule"}


def critique_horizons(analysis: dict, signals: list[dict], events: list[dict], data_health: dict) -> dict:
    signal_map = {x["id"]: x for x in signals}
    fallback = _fallback(analysis, signal_map, data_health)
    if not llm_available(): return fallback
    instruction = """
너는 BTC V4의 독립 Critic이다. Analyst 결론을 공격적으로 검증하되 새로운 시장 데이터나 숫자를 만들지 마라.
검사할 것: (1) 인용 signal이 실제 결론을 지지하는가, (2) NOW와 장기 시간축을 혼동했는가,
(3) 급격한 시장 이벤트를 놓쳤는가, (4) unavailable 데이터를 있는 것처럼 썼는가,
(5) 약한 ML 신호를 과신했는가. 문제가 없으면 passed=true.
JSON: {"passed":true|false,"severity":"low|medium|high","issues":["..."],"warnings":["..."]}
"""
    try:
        result = call_json_agent(instruction, {"analysis": analysis, "signals": signals, "events": events, "data_health": data_health})
        return {
            "passed": bool(result.get("passed", fallback["passed"])),
            "severity": str(result.get("severity", fallback["severity"])),
            "issues": [str(x) for x in result.get("issues", fallback["issues"])][:6],
            "warnings": [str(x) for x in result.get("warnings", fallback["warnings"])][:6],
            "source": "llm",
        }
    except Exception:
        return fallback
