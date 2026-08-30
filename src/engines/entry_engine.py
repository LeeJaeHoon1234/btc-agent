def score_entry(
    technical: dict,
    ml: dict,
    regime: dict,
    similarity: dict,
) -> dict:
    components = {}

    # 35점: 기술적 상태
    technical_component = float(technical.get("score", 50)) * 0.35
    components["technical"] = round(technical_component, 2)

    # 25점: ML. 모델이 없으면 중립값 12.5점
    if ml.get("available"):
        ml_prob = float(ml.get("up_probability", 50))
        ml_component = ml_prob * 0.25
    else:
        ml_component = 12.5
    components["ml"] = round(ml_component, 2)

    # 20점: regime
    regime_component = float(regime.get("bull_score", 50)) * 0.20
    components["regime"] = round(regime_component, 2)

    # 20점: 과거 유사구간
    if similarity.get("available"):
        similar_up_rate = float(similarity.get("up_rate_30d", 50))
        similarity_component = similar_up_rate * 0.20
    else:
        similarity_component = 10.0
    components["similarity"] = round(similarity_component, 2)

    score = round(sum(components.values()), 2)

    if score >= 70:
        label = "strong_entry"
    elif score >= 55:
        label = "watch_entry"
    elif score <= 35:
        label = "avoid_entry"
    else:
        label = "neutral"

    return {
        "score": score,
        "label": label,
        "components": components,
    }
