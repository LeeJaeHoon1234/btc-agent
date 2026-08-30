def run_cycle_agent(cycle: dict) -> dict:
    stage = cycle.get("stage", "unknown")
    heat = float(cycle.get("heat_score", 0))

    if heat >= 75:
        stance = "top_risk"
        summary = "가격 기반 장기 과열 신호가 여러 개 겹친 상태"
    elif heat >= 50:
        stance = "late_cycle_watch"
        summary = "사이클 후반 가능성을 경계할 구간"
    elif stage in {"early_bull", "mid_bull"}:
        stance = "cycle_supportive"
        summary = "장기 상승 구조가 유지되며 극단 과열은 아직 제한적"
    else:
        stance = "uncertain"
        summary = "사이클 방향 확인이 더 필요한 상태"

    return {
        "stance": stance,
        "summary": summary,
        "heat_score": heat,
        "stage": stage,
        "note": cycle.get("note"),
    }
