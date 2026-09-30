def score_entry(
    technical: dict,
    regime: dict,
    similarity: dict,
) -> dict:
    components = {}

    # Transparent, data-derived components only. Missing evidence stays neutral.
    # Weights sum to 100 and are intentionally explicit for auditability.
    technical_component = float(technical.get("score", 50)) * 0.45
    components["technical"] = round(technical_component, 2)

    regime_component = float(regime.get("bull_score", 50)) * 0.25
    components["regime"] = round(regime_component, 2)

    if similarity.get("available"):
        similar_up_rate = float(similarity.get("up_rate_30d", 50))
        similarity_component = similar_up_rate * 0.30
    else:
        similarity_component = 15.0
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
