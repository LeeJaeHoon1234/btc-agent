from __future__ import annotations

from src.agents.llm_client import call_json_agent, llm_available


def refine_reflections(reflections: list[dict]) -> list[dict]:
    """Turn realized prediction outcomes into reusable reasoning lessons.

    The LLM may refine attention, but it cannot change realized returns, grades,
    or quantitative thresholds. If the call is unavailable/budgeted out the
    deterministic journal lessons remain valid.
    """
    if not reflections or not llm_available():
        return []
    instruction = """
너는 BTC V4.1의 Reflect Agent다. 과거 예측과 실제 결과를 보고 '다음 분석에서 반복 실수를 줄이기 위한 교훈'만 만든다.

중요 규칙:
- 제공된 실제 수익률, horizon, 원래 stance, evidence를 바꾸거나 새 숫자를 만들지 않는다.
- 결과가 맞았다는 이유만으로 reasoning이 완벽했다고 말하지 않는다. 결과와 당시 근거의 논리성을 구분한다.
- 결과가 틀렸다는 이유만으로 당시 합리적인 리스크 관리까지 잘못이라고 단정하지 않는다.
- 자동으로 RSI threshold, 매수 기준, 포지션 비중 같은 수치 규칙을 변경하지 않는다.
- attention_up/down은 '다음 유사 상황에서 먼저 재검토할 evidence domain 또는 signal id' 정도만 적는다.
- 현재 시장 데이터가 과거 교훈보다 항상 우선한다는 전제를 유지한다.
- 최대 4개 reflection만 다룬다.

JSON only:
{"lessons":[{"record_id":"...","lesson":"한국어 1~2문장","attention_up":["signal/domain"],"attention_down":["signal/domain"],"confidence":0.0}]}
"""
    try:
        result = call_json_agent(instruction, {"resolved_predictions": reflections[:4]})
        out = []
        valid = {str(x.get("record_id")) for x in reflections}
        for item in result.get("lessons", []) if isinstance(result, dict) else []:
            rid = str(item.get("record_id") or "")
            if rid not in valid:
                continue
            out.append({
                "record_id": rid,
                "lesson": str(item.get("lesson") or "")[:500],
                "attention_up": [str(x)[:80] for x in (item.get("attention_up") or [])][:4],
                "attention_down": [str(x)[:80] for x in (item.get("attention_down") or [])][:4],
                "confidence": item.get("confidence", 0.6),
            })
        return out
    except Exception:
        return []
