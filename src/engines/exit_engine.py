def _linear_score(value: float, low: float, high: float, max_points: float) -> float:
    if value <= low:
        return 0.0
    if value >= high:
        return max_points
    return (value - low) / (high - low) * max_points


def score_exit(latest: dict, cycle: dict) -> dict:
    """
    현재 버전은 가격/추세 기반 Top Risk Score다.
    온체인 MVRV/LTH/ETF가 연결되면 별도 component를 추가할 예정.
    """
    components: dict[str, float] = {}
    reasons: list[str] = []

    rsi = float(latest.get("rsi14", 50))
    ma200_gap = float(latest.get("ma200_gap_pct", 0))
    ma350_gap = float(latest.get("ma350_gap_pct", 0))
    return_90d = float(latest.get("return_90d", 0))
    return_365d = float(latest.get("return_365d", 0))
    drawdown_30d = float(latest.get("drawdown_30d_pct", 0))
    ma20_slope = float(latest.get("ma20_slope_5d", 0))
    return_7d = float(latest.get("return_7d", 0))
    volume_ratio = float(latest.get("volume_ratio", 1))
    heat = float(cycle.get("heat_score", 0))

    # 1) 장기 valuation proxy 30점
    stretch = 0.0
    stretch += _linear_score(ma200_gap, 20, 70, 15)
    stretch += _linear_score(ma350_gap, 30, 100, 15)
    components["trend_stretch"] = round(stretch, 2)
    if stretch >= 20:
        reasons.append("장기 이동평균 대비 가격 이격이 매우 큼")

    # 2) cycle heat 25점
    cycle_component = heat * 0.25
    components["cycle_heat"] = round(cycle_component, 2)
    if heat >= 60:
        reasons.append("사이클 과열 proxy가 높은 편")

    # 3) momentum euphoria 20점
    momentum = 0.0
    momentum += _linear_score(rsi, 68, 85, 10)
    momentum += _linear_score(return_90d, 35, 120, 5)
    momentum += _linear_score(return_365d, 80, 220, 5)
    components["momentum_euphoria"] = round(momentum, 2)
    if momentum >= 12:
        reasons.append("RSI와 중장기 수익률이 과열 방향")

    # 4) 분배/피로 proxy 10점
    distribution_proxy = 0.0
    if volume_ratio >= 1.5 and return_7d < 0:
        distribution_proxy += 5
    if rsi >= 65 and ma20_slope < 0:
        distribution_proxy += 5
    components["distribution_proxy"] = round(distribution_proxy, 2)
    if distribution_proxy >= 5:
        reasons.append("높은 거래/과열 이후 모멘텀 둔화 징후")

    # 5) 고점 이후 추세붕괴 확인 15점
    # 이미 충분히 상승한 시장에서만 이 점수를 준다.
    reversal = 0.0
    extended_before = return_90d >= 25 or ma200_gap >= 20
    if extended_before:
        if drawdown_30d <= -8:
            reversal += 6
        if drawdown_30d <= -15:
            reversal += 4
        if ma20_slope < 0:
            reversal += 3
        if return_7d <= -8:
            reversal += 2
    components["reversal_confirmation"] = round(min(15, reversal), 2)
    if reversal >= 8:
        reasons.append("과열 이후 가격 추세 훼손이 확인됨")

    score = round(min(100, sum(components.values())), 2)

    if score >= 88:
        label = "critical_exit"
    elif score >= 75:
        label = "strong_exit"
    elif score >= 60:
        label = "exit_watch"
    else:
        label = "hold_cycle"

    return {
        "score": score,
        "label": label,
        "components": components,
        "reasons": reasons,
        "limitations": [
            "MVRV/LTH/ETF Flow/Funding/OI는 아직 실시간 입력에 연결되지 않음"
        ],
    }
