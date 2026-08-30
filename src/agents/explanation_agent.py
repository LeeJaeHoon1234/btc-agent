from src.agents.llm_client import call_json_agent, llm_available


def _market_state_text(regime: str | None) -> str:
    mapping = {
        "bull_trend": "상승 흐름이 뚜렷한 장",
        "bull_transition": "상승 전환을 확인하는 장",
        "sideways": "방향이 아직 확실하지 않은 장",
        "bear_transition": "하락 전환을 경계하는 장",
        "bear_trend": "하락 흐름이 강한 장",
    }
    return mapping.get(regime, "시장 방향을 더 확인해야 하는 장")


def _entry_text(score: float) -> str:
    if score >= 80:
        return "매수 조건이 강하게 모인 상태"
    if score >= 70:
        return "매수 조건이 충족된 상태"
    if score >= 65:
        return "매수 조건에 거의 도달한 상태"
    if score >= 55:
        return "일부 매수 신호는 있지만 확신이 부족한 상태"
    return "지금은 신규 매수 매력이 낮은 상태"


def _exit_text(score: float) -> str:
    if score >= 88:
        return "사이클 고점 위험이 매우 높은 상태"
    if score >= 75:
        return "고점 위험이 높아 적극적인 익절 검토가 필요한 상태"
    if score >= 60:
        return "고점 위험이 올라와 익절을 준비할 상태"
    if score >= 40:
        return "일부 과열 신호가 있지만 아직 강한 고점 신호는 아닌 상태"
    return "현재 고점 위험은 낮은 상태"


def _fallback_explanation(state) -> dict:
    decision = state.final_decision
    latest = state.latest
    entry_score = float(state.entry.get("score", 50))
    exit_score = float(state.exit.get("score", 0))
    regime = state.regime.get("regime")

    rsi = float(latest.get("rsi14", 50))
    ma20_gap = float(latest.get("ma20_gap_pct", 0))
    volume_ratio = float(latest.get("volume_ratio", 1))
    ma200_gap = float(latest.get("ma200_gap_pct", 0))
    ma200_slope = float(latest.get("ma200_slope_20d", 0))

    positives: list[str] = []
    cautions: list[str] = []

    if ma200_gap > 0:
        positives.append("가격이 장기 기준선 위에 있어 큰 흐름은 무너지지 않았습니다.")
    else:
        cautions.append("가격이 장기 기준선 아래라 큰 흐름이 아직 약합니다.")

    ml = state.ml
    if ml.get("available"):
        ml_prob = float(ml.get("up_probability", 50))
        mean_auc = ml.get("metadata", {}).get("walk_forward_mean_auc")
        if ml_prob >= 60:
            positives.append(f"AI 모델은 향후 30일을 상승 쪽({ml_prob:.0f}%)으로 보고 있습니다.")
        elif ml_prob <= 40:
            cautions.append(f"AI 모델은 향후 30일 상승 가능성을 낮게({ml_prob:.0f}%) 보고 있습니다.")

        if mean_auc is not None:
            mean_auc = float(mean_auc)
            if mean_auc < 0.57:
                cautions.append("다만 AI 모델의 과거 검증 성능이 강하지 않아 이 확률만 믿고 매매하면 안 됩니다.")
            elif mean_auc >= 0.62:
                positives.append("AI 모델의 과거 검증 성능도 비교적 양호한 편입니다.")

    similarity = state.similarity
    if similarity.get("available"):
        up_rate = float(similarity.get("up_rate_30d", 50))
        avg_forward = float(similarity.get("avg_forward_return_30d", 0))
        dispersion = float(similarity.get("dispersion_30d", 0))
        if up_rate >= 70 and avg_forward > 0:
            positives.append(
                f"과거 비슷한 구간은 30일 뒤 상승한 경우가 {up_rate:.0f}%였고 평균 수익률도 플러스였습니다."
            )
        if dispersion >= 18:
            cautions.append("다만 과거 비슷한 구간들의 결과 차이가 커서 같은 흐름이 반복된다고 단정하기 어렵습니다.")

    if rsi >= 70:
        cautions.append(f"단기적으로 많이 오른 상태입니다(RSI {rsi:.0f}). 지금 따라 사면 눌림을 맞을 수 있습니다.")
    elif rsi <= 35:
        positives.append(f"단기적으로 많이 눌린 상태라 반등 여지가 있습니다(RSI {rsi:.0f}).")

    if ma20_gap >= 8:
        cautions.append(f"최근 평균 가격보다 약 {ma20_gap:.1f}% 위라 단기 추격매수 부담이 있습니다.")

    if volume_ratio < 0.7:
        cautions.append(f"거래량이 최근 평균의 약 {volume_ratio * 100:.0f}% 수준이라 상승 확인이 약합니다.")
    elif volume_ratio >= 1.2:
        positives.append(f"거래량이 최근 평균보다 높아 현재 움직임에 힘이 실리고 있습니다.")

    if ma200_slope < 0 and ma200_gap > 0:
        cautions.append("가격은 장기 기준선 위지만 그 기준선 자체는 아직 내려가고 있어 완전한 상승 전환으로 보긴 이릅니다.")

    # 중복/과다 출력을 줄인다.
    positives = positives[:4]
    cautions = cautions[:4]

    if decision.action == "매수":
        headline = "지금은 분할 매수를 검토할 수 있습니다."
        strategy = [
            "신규 매수: 한 번에 전부 사기보다 분할 접근",
            "기존 보유: 유지",
            "익절: 고점 위험이 크게 오르기 전까지 서두르지 않기",
        ]
    elif decision.action == "비중축소":
        headline = "지금은 수익을 지키는 쪽이 더 중요합니다."
        strategy = [
            "신규 매수: 보류",
            "기존 보유: 일부 분할 익절 검토",
            "추가 대응: 고점 위험과 추세 회복 여부를 함께 확인",
        ]
    else:
        headline = "지금은 새로 따라 사기보다 조금 더 확인하는 편이 낫습니다."
        strategy = [
            "신규 매수: 일단 대기",
            "기존 보유: 급하게 줄일 필요는 낮음",
            "익절: 현재 고점 위험이 낮다면 서두르지 않기",
        ]

    if entry_score >= 65 and entry_score < 70:
        headline = "매수 조건은 거의 왔지만, 지금은 한 번 더 확인할 자리입니다."

    summary = (
        f"{_entry_text(entry_score)}이고, {_exit_text(exit_score)}입니다. "
        f"현재 시장은 {_market_state_text(regime)}으로 판단됐습니다."
    )

    recheck: list[str] = []
    if decision.invalidation:
        # fallback에서도 정량화된 자연어를 최대한 유지하되 원문을 그대로 노출하지 않는다.
        if entry_score < 70:
            recheck.append("매수 점수가 70을 확실히 넘고 상승 추세가 더 선명해지는지 확인")
        if rsi >= 70:
            recheck.append("단기 과열이 식은 뒤 가격이 지지되는지 확인")
        if ma200_gap > 0:
            recheck.append("가격이 장기 기준선 위를 계속 지키는지 확인")
        if exit_score < 60:
            recheck.append("고점 위험 점수가 60 이상으로 빠르게 올라오는지 확인")

    return {
        "headline": headline,
        "summary": summary,
        "positives": positives,
        "cautions": cautions,
        "strategy": strategy,
        "recheck": recheck[:4],
        "source": "rule",
    }


def explain_for_user(state) -> dict:
    """
    최종 판단을 쉬운 한국어로 번역한다.
    이 Agent는 새로운 투자 판단을 만들거나 수치를 재계산하지 않는다.
    """
    fallback = _fallback_explanation(state)

    if not llm_available():
        return fallback

    instruction = """
너는 BTC Explanation Agent다.
이미 확정된 최종 판단을 비전문가가 바로 이해할 수 있는 쉬운 한국어로 번역한다.
새로운 투자 판단을 만들지 말고 final_decision의 action을 절대 변경하지 마라.
입력 숫자를 새로 계산하거나 수정하지 마라.
AUC, dispersion, regime, stance, invalidation 같은 전문용어는 가능한 한 쉬운 말로 풀어 써라.
단, 필요한 숫자(RSI, 매수 점수, 고점 위험 점수, AI 상승확률)는 이해에 도움이 될 때만 사용한다.
문장은 짧게 쓰고, 과도한 확신 표현을 피한다.

반환 형식:
{
  "headline": "현재 결론을 쉬운 한 문장으로",
  "summary": "왜 그런지 2문장 이내",
  "positives": ["좋은 신호 1", "좋은 신호 2"],
  "cautions": ["주의 신호 1", "주의 신호 2"],
  "strategy": ["신규 매수: ...", "기존 보유: ...", "익절: ..."],
  "recheck": ["다시 판단할 조건 1", "다시 판단할 조건 2"]
}
"""

    payload = state.compact_context() | {
        "final_decision": state.final_decision.to_dict(),
        "critic_feedback": [c.to_dict() for c in state.critiques],
    }

    try:
        result = call_json_agent(instruction, payload)
        return {
            "headline": str(result.get("headline", fallback["headline"])),
            "summary": str(result.get("summary", fallback["summary"])),
            "positives": list(result.get("positives", fallback["positives"]))[:4],
            "cautions": list(result.get("cautions", fallback["cautions"]))[:4],
            "strategy": list(result.get("strategy", fallback["strategy"]))[:4],
            "recheck": list(result.get("recheck", fallback["recheck"]))[:4],
            "source": "llm",
        }
    except Exception as e:
        state.add_log(f"Explanation LLM fallback: {e}")
        return fallback
