from src.agents.llm_client import call_json_agent, llm_available
from src.core.schemas import Decision


def _rule_decision(state) -> Decision:
    entry_score = float(state.entry.get("score", 50))
    exit_score = float(state.exit.get("score", 0))
    risk_level = state.risk.get("level", "medium")

    reasons = []
    invalidation = []

    if exit_score >= 75:
        action = "비중축소"
        confidence = min(0.92, 0.60 + exit_score / 250)
        thesis = "사이클 과열 또는 고점 이후 훼손 신호가 강해 방어가 우선"
        reasons.extend(state.exit.get("reasons", []))
        invalidation.append("고점 위험 점수가 빠르게 낮아지고 장기 추세가 재강화될 경우")
    elif entry_score >= 70 and risk_level != "high":
        action = "매수"
        confidence = min(0.90, 0.58 + entry_score / 300)
        thesis = "기술/Regime/ML/유사구간의 종합 진입 점수가 우호적"
        reasons.extend(state.technical.get("reasons", [])[:3])
        invalidation.append("MA200 재이탈 또는 Regime이 bear 방향으로 전환될 경우")
    else:
        action = "관망"
        confidence = 0.62
        thesis = "진입 또는 익절 어느 한쪽으로 충분한 확신이 모이지 않음"
        if state.gate:
            reasons.extend(state.gate.reasons[:3])
        invalidation.append("Entry 또는 Exit score가 임계치를 명확히 돌파할 경우")

    return Decision(
        action=action,
        confidence=round(confidence, 2),
        thesis=thesis,
        reasons=reasons,
        invalidation=invalidation,
        source="rule",
    )


def make_decision(state) -> Decision:
    fallback = _rule_decision(state)

    if state.gate is None or state.gate.route != "deep_analysis" or not llm_available():
        return fallback

    instruction = """
너는 BTC Decision Agent다.
목표는 수익을 보장하는 것이 아니라, 주어진 신호의 충돌을 정리해
매수/관망/비중축소 중 하나를 선택하는 것이다.
ML 확률은 보조 신호이며 낮은 Walk-Forward AUC면 비중을 낮춰 해석한다.
Exit score가 높으면 상승 여력이 있어 보여도 고점 리스크를 반드시 반영한다.

반환 형식:
{
  "action": "매수|관망|비중축소",
  "confidence": 0.0~1.0,
  "thesis": "한 문장",
  "reasons": ["..."],
  "invalidation": ["..."]
}
"""

    try:
        result = call_json_agent(instruction, state.compact_context())
        return Decision(
            action=str(result.get("action", fallback.action)),
            confidence=float(result.get("confidence", fallback.confidence)),
            thesis=str(result.get("thesis", fallback.thesis)),
            reasons=list(result.get("reasons", fallback.reasons)),
            invalidation=list(result.get("invalidation", fallback.invalidation)),
            source="llm",
        )
    except Exception as e:
        state.add_log(f"Decision LLM fallback: {e}")
        return fallback


def revise_decision(state, current: Decision, critique) -> Decision:
    if critique.passed:
        return current

    if not llm_available():
        # LLM이 없으면 보수적으로 한 단계 관망 방향으로 이동
        if critique.severity == "high" and current.action == "매수":
            return Decision(
                action="관망",
                confidence=max(0.45, current.confidence - 0.15),
                thesis="Critic이 중대한 충돌을 발견하여 매수 판단을 보수적으로 수정",
                reasons=current.reasons + critique.issues,
                invalidation=current.invalidation,
                source="rule_revision",
            )
        return current

    instruction = """
너는 BTC Decision Agent의 Revision 단계다.
기존 결정과 Critic의 지적을 보고 결정을 수정하라.
Critic의 말을 무조건 따르지 말고 입력 데이터와 충돌 여부를 확인하라.

반환 형식:
{
  "action": "매수|관망|비중축소",
  "confidence": 0.0~1.0,
  "thesis": "한 문장",
  "reasons": ["..."],
  "invalidation": ["..."]
}
"""

    payload = state.compact_context() | {
        "current_decision": current.to_dict(),
        "critique": critique.to_dict(),
    }

    try:
        result = call_json_agent(instruction, payload)
        return Decision(
            action=str(result.get("action", current.action)),
            confidence=float(result.get("confidence", current.confidence)),
            thesis=str(result.get("thesis", current.thesis)),
            reasons=list(result.get("reasons", current.reasons)),
            invalidation=list(result.get("invalidation", current.invalidation)),
            source="llm_revision",
        )
    except Exception as e:
        state.add_log(f"Revision LLM fallback: {e}")
        return current
