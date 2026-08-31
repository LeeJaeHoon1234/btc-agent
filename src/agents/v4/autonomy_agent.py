from __future__ import annotations

from copy import deepcopy

from src.agents.llm_client import call_json_agent, llm_available
from src.engines.v4.horizon_engine import HORIZONS

ALLOWED_STANCES = {"POSITIVE", "NEUTRAL", "CAUTION", "NEGATIVE"}


def _validate(result: dict, fallback: dict, valid_ids: set[str]) -> dict:
    out = deepcopy(fallback)
    horizons = result.get("horizons", {}) if isinstance(result, dict) else {}
    for h in HORIZONS:
        candidate = horizons.get(h, {}) if isinstance(horizons, dict) else {}
        if not isinstance(candidate, dict):
            continue
        stance = str(candidate.get("stance", out[h]["stance"])).upper()
        if stance not in ALLOWED_STANCES:
            stance = out[h]["stance"]
        ids = [str(x) for x in candidate.get("key_signal_ids", []) if str(x) in valid_ids][:5]
        if not ids:
            ids = out[h]["key_signal_ids"]
        try:
            confidence = max(0.2, min(.92, float(candidate.get("confidence", out[h]["confidence"]))))
        except (TypeError, ValueError):
            confidence = out[h]["confidence"]
        out[h].update({
            "stance": stance,
            "confidence": confidence,
            "headline": str(candidate.get("headline", out[h]["headline"]))[:180],
            "summary": str(candidate.get("summary", out[h]["summary"]))[:420],
            "key_signal_ids": ids,
            "good": [str(x)[:180] for x in candidate.get("good", out[h].get("good", []))][:2],
            "risks": [str(x)[:180] for x in candidate.get("risks", out[h].get("risks", []))][:2],
            "source": "llm",
        })
    global_view = result.get("global_view", {}) if isinstance(result, dict) else {}
    return {
        "horizons": out,
        "global_view": {
            "what_changed": str(global_view.get("what_changed", ""))[:280],
            "most_important": str(global_view.get("most_important", ""))[:280],
            "conflict": str(global_view.get("conflict", ""))[:280],
        },
        "source": "llm",
    }


def analyze_horizons(
    signals: list[dict],
    events: list[dict],
    fallbacks: dict,
    data_health: dict,
    specialist_views: dict | None = None,
    memory: dict | None = None,
) -> dict:
    base = {"horizons": fallbacks, "global_view": {"what_changed": "", "most_important": "", "conflict": ""}, "source": "fallback"}
    if not llm_available():
        return base
    instruction = """
너는 BTC V4.1의 Senior Market Analyst다. 숫자 계산기가 아니라 '지금 무엇이 중요한지' 고르는 분석가다.
입력의 signal 값과 event만 사실로 사용할 수 있다. 숫자를 만들거나 수정하지 마라.

중요한 자율성 규칙:
- 모든 지표를 나열하지 말고 현재 상황을 설명하는 핵심 증거 1~5개만 직접 선택한다.
- specialist_views는 서로 독립적으로 자기 영역만 본 의견이다. 단순 평균하지 말고 근거의 최신성/관련성/불확실성을 판단한다.
- specialist의 내부 score나 이전 최종 행동에 끌리지 않는다. 최종 행동은 이 단계에서 결정하지 않는다.
- memory는 과거 자기 판단에서 얻은 '약한 prior'일 뿐이다. 현재 데이터와 충돌하면 반드시 현재 데이터를 우선한다.
- performance_matrix의 샘플이 적으면 신뢰하지 않는다. 샘플 3개 미만은 거의 참고하지 않는다.

시간축 규칙:
- NOW/TODAY/1W/1M/1Y는 서로 다른 결론이어도 된다.
- NOW/TODAY에서는 급락→반등, 거래량, 체결/호가, 단기 레버리지 변화를 장기 이동평균보다 우선할 수 있다.
- 1W에서는 단기 추세, 파생, 이벤트 지속성을 함께 본다.
- 1M/1Y에서는 일중 잡음보다 장기 추세, 사이클, 거시, 자금 흐름, 네트워크를 더 중시한다.
- ML은 검증 성능이 약하면 보조 증거로만 취급한다. 누락 데이터는 추측하지 않는다.
- 전문용어는 사용자 문장에 남발하지 말고 쉬운 한국어로 풀어라.
- 각 horizon 결론은 반드시 제공된 signal ID를 1~5개 인용한다.

JSON 형식:
{
  "global_view": {"what_changed":"지금 시장에서 가장 눈에 띄는 변화", "most_important":"가장 중요한 해석", "conflict":"충돌하는 신호가 있으면 짧게"},
  "horizons": {
    "NOW": {"stance":"POSITIVE|NEUTRAL|CAUTION|NEGATIVE", "confidence":0.0, "headline":"짧은 말", "summary":"최대 2문장", "key_signal_ids":["S_..."], "good":["최대2"], "risks":["최대2"]},
    "TODAY": {}, "1W": {}, "1M": {}, "1Y": {}
  }
}
"""
    payload = {
        "signals": signals,
        "events": events,
        "data_health": data_health,
        "independent_specialist_views": specialist_views or {},
        "reflection_memory": memory or {},
    }
    try:
        result = call_json_agent(instruction, payload)
        return _validate(result, fallbacks, {s["id"] for s in signals})
    except Exception:
        return base
