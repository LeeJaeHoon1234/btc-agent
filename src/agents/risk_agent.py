def run_risk_agent(state) -> dict:
    risks: list[str] = []
    severity_score = 0

    latest = state.latest
    regime = state.regime
    exit_signal = state.exit
    similarity = state.similarity
    research = state.research
    experts = state.experts

    if float(latest.get("volatility_30d_pct", 0)) >= 70:
        risks.append("30일 연율화 변동성이 매우 높음")
        severity_score += 20

    if regime.get("regime") in {"bull_transition", "bear_transition", "sideways"}:
        risks.append("Regime 전환 구간이라 가짜 돌파/이탈 가능성")
        severity_score += 15

    if not similarity.get("available"):
        risks.append("비교 가능한 과거 유사구간이 부족함")
        severity_score += 8

    if float(exit_signal.get("score", 0)) >= 75:
        risks.append("장기 과열/고점 위험 점수가 높음")
        severity_score += 25

    if similarity.get("available") and float(similarity.get("dispersion_30d", 0)) >= 20:
        risks.append("과거 유사구간 결과가 서로 크게 달랐음")
        severity_score += 12

    if research:
        if float(research.get("confidence", 0)) < 0.4:
            risks.append("Autonomous research confidence is low or important sources are unavailable")
            severity_score += 8
        if research.get("stance") == "BEARISH":
            risks.append("Cross-domain research is bearish")
            severity_score += 12

    derivatives = experts.get("derivatives", {}) if isinstance(experts, dict) else {}
    if derivatives.get("available") and derivatives.get("regime") in {"LEVERAGED_BULL", "BEARISH_LEVERAGE", "LONG_FLUSH"}:
        risks.append(f"Derivatives regime: {derivatives.get('regime')}")
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
