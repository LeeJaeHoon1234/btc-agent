def run_risk_agent(state) -> dict:
    risks: list[str] = []
    severity_score = 0

    latest = state.latest
    regime = state.regime
    ml = state.ml
    exit_signal = state.exit
    similarity = state.similarity

    if float(latest.get("volatility_30d_pct", 0)) >= 70:
        risks.append("30일 연율화 변동성이 매우 높음")
        severity_score += 20

    if regime.get("regime") in {"bull_transition", "bear_transition", "sideways"}:
        risks.append("Regime 전환 구간이라 가짜 돌파/이탈 가능성")
        severity_score += 15

    if ml.get("available"):
        mean_auc = ml.get("metadata", {}).get("walk_forward_mean_auc")
        if mean_auc is not None and float(mean_auc) < 0.52:
            risks.append("ML Walk-Forward 성능이 약해 확률을 강하게 믿기 어려움")
            severity_score += 15
    else:
        risks.append("ML 신호가 없는 상태")
        severity_score += 8

    if float(exit_signal.get("score", 0)) >= 75:
        risks.append("장기 과열/고점 위험 점수가 높음")
        severity_score += 25

    if similarity.get("available") and float(similarity.get("dispersion_30d", 0)) >= 20:
        risks.append("과거 유사구간 결과가 서로 크게 달랐음")
        severity_score += 12

    severity_score = min(100, severity_score)

    if severity_score >= 60:
        level = "high"
    elif severity_score >= 30:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "score": severity_score,
        "risks": risks,
    }
