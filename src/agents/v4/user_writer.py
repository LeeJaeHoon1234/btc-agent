from __future__ import annotations

from src.agents.llm_client import call_json_agent, llm_available


def _action_fallback(horizons: dict, events: list[dict]) -> dict:
    now = horizons.get("NOW", {}); today = horizons.get("TODAY", {}); month = horizons.get("1M", {})
    acute = any(e.get("severity", 0) >= 3 for e in events)
    if month.get("stance") == "NEGATIVE" and today.get("stance") == "NEGATIVE": hold = "줄이기 검토"
    else: hold = "유지"
    if now.get("stance") == "POSITIVE" and today.get("stance") == "POSITIVE" and not acute: add = "분할매수 검토"
    else: add = "기다림"
    if month.get("stance") == "NEGATIVE": profit = "일부 검토"
    else: profit = "서두르지 않음"
    headline = (events[0].get("title") if events else None) or now.get("headline") or "현재 흐름을 확인 중입니다."
    summary = now.get("summary") or today.get("summary") or "확인 가능한 데이터가 제한적입니다."
    return {
        "headline": headline, "summary": summary,
        "actions": {"hold": hold, "add": add, "take_profit": profit},
        "why": (now.get("good", []) + now.get("risks", []))[:3],
        "watch": ["가격 흐름과 거래량이 현재 방향을 유지하는지 확인", "파생시장 과열이나 반전 신호가 생기는지 확인"],
        "source": "fallback",
    }


def write_user_view(analysis: dict, signals: list[dict], events: list[dict], critic: dict) -> dict:
    horizons = analysis.get("horizons", {})
    fallback = _action_fallback(horizons, events)
    if not llm_available(): return fallback
    instruction = """
너는 BTC V4.1의 최종 사용자 Writer다. 전문 분석 결과를 한국어 비전문가가 5초 안에 이해하도록 번역한다.
새 분석을 하지 말고 Analyst와 Critic의 범위 안에서만 써라. 숫자를 새로 만들지 마라.
규칙:
- 전문용어는 가능한 쓰지 않는다. funding/OI/VWAP/regime 같은 내부 용어는 메인 문장에 쓰지 말고 쉬운 뜻으로 번역한다.
- headline은 '지금 무슨 일이 벌어지는지' 한 문장. 숫자 이름을 나열하지 말고 상황을 말한다.
- summary 최대 2문장. 첫 문장은 좋은 점/나쁜 점, 마지막 문장은 행동 의미가 바로 읽히게 쓴다.
- 동일 근거 반복 금지.
- 숫자는 정말 중요한 것 최대 3개만.
- 내부 Agent/Planner/score/Research Delta/AUC 같은 개발자 용어는 메인 문장에 쓰지 않는다.
- actions는 기존 보유 / 추가매수 / 익절을 서로 별도로 표현한다.
- 확정 수익처럼 말하지 않는다.
JSON:
{"headline":"...","summary":"...","actions":{"hold":"유지|줄이기 검토","add":"기다림|분할매수 검토|피하기","take_profit":"서두르지 않음|일부 검토|적극 검토"},"why":["최대3"],"watch":["최대3"],"source":"llm"}
"""
    try:
        result = call_json_agent(instruction, {"analysis": analysis, "events": events[:4], "critic": critic, "signals": signals})
        actions = result.get("actions", {}) if isinstance(result.get("actions"), dict) else {}
        return {
            "headline": str(result.get("headline", fallback["headline"]))[:180],
            "summary": str(result.get("summary", fallback["summary"]))[:420],
            "actions": {
                "hold": str(actions.get("hold", fallback["actions"]["hold"]))[:60],
                "add": str(actions.get("add", fallback["actions"]["add"]))[:60],
                "take_profit": str(actions.get("take_profit", fallback["actions"]["take_profit"]))[:60],
            },
            "why": [str(x)[:180] for x in result.get("why", fallback["why"])][:3],
            "watch": [str(x)[:180] for x in result.get("watch", fallback["watch"])][:3],
            "source": "llm",
        }
    except Exception:
        return fallback
