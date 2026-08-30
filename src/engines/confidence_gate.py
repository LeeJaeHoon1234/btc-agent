from config.thresholds import (
    ENTRY_DEEP_MARGIN,
    ENTRY_STRONG,
    EXIT_DEEP_MARGIN,
    EXIT_STRONG,
    EXIT_WARNING,
    GATE_FAST_CONFIDENCE,
    GATE_MIN_MODEL_AUC,
)
from src.core.schemas import GateResult


def _near_threshold(value: float, threshold: float, margin: float) -> bool:
    return abs(value - threshold) <= margin


def evaluate_confidence_gate(
    technical: dict,
    ml: dict,
    regime: dict,
    similarity: dict,
    entry: dict,
    exit_signal: dict,
) -> GateResult:
    confidence = 0.86
    reasons: list[str] = []
    force_deep_reasons: list[str] = []

    technical_score = float(technical.get("score", 50))
    entry_score = float(entry.get("score", 50))
    exit_score = float(exit_signal.get("score", 0))

    # 1) Technical vs ML conflict
    if ml.get("available"):
        ml_prob = float(ml.get("up_probability", 50))
        technical_bull = technical_score >= 60
        ml_bull = ml_prob >= 55

        if technical_bull != ml_bull:
            confidence -= 0.16
            reasons.append("기술적 판단과 ML 방향이 충돌")
            force_deep_reasons.append("기술적 판단과 ML 방향 충돌")

        mean_auc = ml.get("metadata", {}).get("walk_forward_mean_auc")
        if mean_auc is not None and float(mean_auc) < GATE_MIN_MODEL_AUC:
            confidence -= 0.12
            reasons.append("Walk-Forward 평균 AUC가 낮아 ML 신뢰를 축소")
    else:
        confidence -= 0.10
        reasons.append("저장된 ML 모델이 없어 ML 신호를 사용하지 못함")

    # 2) Regime uncertainty
    if regime.get("regime") in {"bull_transition", "bear_transition", "sideways"}:
        confidence -= 0.10
        reasons.append("시장 Regime이 전환/횡보 상태")

    # 3) Similarity uncertainty
    if similarity.get("available"):
        dispersion = float(similarity.get("dispersion_30d", 0))
        if dispersion >= 20:
            confidence -= 0.08
            reasons.append("유사구간의 30일 결과 분산이 큼")

    # 4) Entry/Exit conflict
    if entry_score >= 65 and exit_score >= 60:
        confidence -= 0.18
        reasons.append("진입 신호와 사이클 익절 신호가 동시에 강함")
        force_deep_reasons.append("진입 신호와 고점 위험 신호가 동시에 강함")

    # 5) Decision boundary: Entry
    if _near_threshold(entry_score, ENTRY_STRONG, ENTRY_DEEP_MARGIN):
        force_deep_reasons.append(
            f"Entry Score {entry_score:.1f}이 매수 임계값 {ENTRY_STRONG} 근처"
        )

    # 6) Decision boundary: Exit
    if _near_threshold(exit_score, EXIT_WARNING, EXIT_DEEP_MARGIN):
        force_deep_reasons.append(
            f"Exit Score {exit_score:.1f}이 경고 임계값 {EXIT_WARNING} 근처"
        )

    if _near_threshold(exit_score, EXIT_STRONG, EXIT_DEEP_MARGIN):
        force_deep_reasons.append(
            f"Exit Score {exit_score:.1f}이 강한 익절 임계값 {EXIT_STRONG} 근처"
        )

    # 7) Strong exit risk
    if exit_score >= EXIT_STRONG:
        confidence -= 0.06
        reasons.append("사이클 고점 위험이 높아 추가 검증 필요")
        force_deep_reasons.append("강한 사이클 고점 위험")

    confidence = max(0.20, min(0.95, confidence))

    if force_deep_reasons:
        route = "deep_analysis"
        for reason in force_deep_reasons:
            if reason not in reasons:
                reasons.append(reason)
    elif confidence < GATE_FAST_CONFIDENCE:
        route = "deep_analysis"
    else:
        route = "fast_path"

    return GateResult(
        route=route,
        confidence=round(confidence, 2),
        reasons=reasons,
    )
