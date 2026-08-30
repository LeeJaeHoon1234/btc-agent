from src.agents.llm_client import call_json_agent, llm_available
from src.core.schemas import Critique, Decision


def _rule_critique(state, decision: Decision) -> Critique:
    issues: list[str] = []
    instructions: list[str] = []
    severity_points = 0

    entry_score = float(state.research_adjustment.get("adjusted_entry_score", state.entry.get("score", 50)))
    exit_score = float(state.research_adjustment.get("adjusted_exit_score", state.exit.get("score", 0)))
    regime = state.regime.get("regime")

    if decision.action == "매수" and exit_score >= 70:
        issues.append("매수 판단인데 Exit score가 높아 고점 리스크와 충돌")
        instructions.append("매수 비중을 낮추거나 관망으로 수정할지 검토")
        severity_points += 3

    if decision.action == "매수" and regime in {"bear_trend", "bear_transition"}:
        issues.append("매수 판단이 약세 Regime과 충돌")
        instructions.append("추세 회복 확인 조건을 invalidation/조건부 진입에 추가")
        severity_points += 3

    if decision.action == "비중축소" and exit_score < 45:
        issues.append("비중축소 판단에 비해 Exit score가 낮음")
        instructions.append("과도한 조기 익절인지 재검토")
        severity_points += 2

    if decision.action == "매수" and entry_score < 60:
        issues.append("매수 판단에 비해 Entry score가 충분히 높지 않음")
        severity_points += 2

    research_score = float(state.research.get("score", 0)) if state.research else 0
    if decision.action == "매수" and research_score <= -20:
        issues.append("매수 판단이 cross-domain research와 강하게 충돌")
        instructions.append("외부 근거 충돌을 해소하거나 매수 비중을 낮출지 검토")
        severity_points += 3

    if decision.action == "비중축소" and research_score >= 25:
        issues.append("비중축소 판단이 우호적인 cross-domain research와 충돌")
        severity_points += 2

    if not decision.invalidation:
        issues.append("판단이 틀렸음을 인정할 무효화 조건이 없음")
        instructions.append("구체적인 invalidation 조건을 추가")
        severity_points += 1

    if severity_points >= 5:
        severity = "high"
    elif severity_points >= 2:
        severity = "medium"
    else:
        severity = "low"

    return Critique(
        passed=severity_points == 0,
        severity=severity,
        issues=issues,
        revision_instructions=instructions,
        source="rule",
    )


def review_decision(state, decision: Decision) -> Critique:
    fallback = _rule_critique(state, decision)

    if state.gate is None or state.gate.route != "deep_analysis" or not llm_available():
        return fallback

    instruction = """
너는 BTC Critic Agent다.
Decision Agent의 결정을 공격적으로 검증하되 억지 반대는 하지 마라.
특히 다음을 검사한다.
1) Entry와 Exit 신호의 충돌
2) 낮은 ML 신뢰도를 과대해석했는지
3) Regime과 행동이 충돌하는지
4) 과열/고점 위험을 누락했는지
5) invalidation 조건이 부족한지

반환 형식:
{
  "passed": true|false,
  "severity": "low|medium|high",
  "issues": ["..."],
  "revision_instructions": ["..."]
}
"""

    payload = state.compact_context() | {"decision": decision.to_dict()}

    try:
        result = call_json_agent(instruction, payload)
        return Critique(
            passed=bool(result.get("passed", fallback.passed)),
            severity=str(result.get("severity", fallback.severity)),
            issues=list(result.get("issues", fallback.issues)),
            revision_instructions=list(
                result.get("revision_instructions", fallback.revision_instructions)
            ),
            source="llm",
        )
    except Exception as e:
        state.add_log(f"Critic LLM fallback: {e}")
        return fallback
