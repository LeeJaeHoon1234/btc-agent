from src.core.schemas import Decision


def apply_position_plan(decision: Decision, entry_score: float, exit_score: float) -> Decision:
    """행동 방향을 실제 비중 변화 제안으로 변환한다."""

    if decision.action == "매수":
        if entry_score >= 82 and decision.confidence >= 0.80:
            size = 30.0
        elif entry_score >= 70:
            size = 20.0
        else:
            size = 10.0

    elif decision.action == "비중축소":
        if exit_score >= 88:
            size = -50.0
        elif exit_score >= 75:
            size = -30.0
        else:
            size = -15.0

    else:
        size = 0.0

    decision.action_size_pct = size
    return decision
