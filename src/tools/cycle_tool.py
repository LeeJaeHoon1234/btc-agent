import pandas as pd


def analyze_cycle(df: pd.DataFrame) -> dict:
    latest = df.dropna(
        subset=[
            "ma111",
            "ma200",
            "ma350",
            "pi_cycle_ratio",
            "drawdown_from_ath_pct",
            "return_365d",
        ]
    ).iloc[-1]

    rsi = float(latest["rsi14"])
    ma200_gap = float(latest["ma200_gap_pct"])
    ma350_gap = float(latest["ma350_gap_pct"])
    pi_ratio = float(latest["pi_cycle_ratio"])
    return_365d = float(latest["return_365d"])
    drawdown = float(latest["drawdown_from_ath_pct"])

    # 가격 기반 cycle proxy. MVRV/LTH/ETF 같은 외부 온체인 데이터는 아직 연결하지 않는다.
    heat = 0
    reasons: list[str] = []

    if rsi >= 80:
        heat += 20
        reasons.append("RSI가 극단 과열 영역")
    elif rsi >= 70:
        heat += 10
        reasons.append("RSI가 과열 영역")

    if ma200_gap >= 60:
        heat += 25
        reasons.append("가격이 MA200에서 매우 크게 이격")
    elif ma200_gap >= 35:
        heat += 15
        reasons.append("가격이 MA200에서 크게 이격")

    if ma350_gap >= 80:
        heat += 20
        reasons.append("가격이 장기 MA350에서 크게 이격")
    elif ma350_gap >= 50:
        heat += 10
        reasons.append("가격이 장기 MA350 위로 확장")

    if pi_ratio >= 0.95:
        heat += 25
        reasons.append("Pi Cycle 두 장기선이 매우 근접")
    elif pi_ratio >= 0.85:
        heat += 12
        reasons.append("Pi Cycle proxy가 과열 방향으로 접근")

    if return_365d >= 150:
        heat += 10
        reasons.append("1년 수익률이 매우 높음")
    elif return_365d >= 80:
        heat += 5
        reasons.append("1년 수익률이 높은 편")

    heat = min(100, heat)

    if drawdown <= -35 and ma200_gap < 0:
        stage = "bear_or_accumulation"
    elif ma200_gap >= 0 and heat < 25:
        stage = "early_bull"
    elif 25 <= heat < 50:
        stage = "mid_bull"
    elif 50 <= heat < 75:
        stage = "late_bull"
    else:
        stage = "euphoria_risk"

    return {
        "stage": stage,
        "heat_score": heat,
        "pi_cycle_ratio": pi_ratio,
        "pi_cycle_distance_pct": float(latest["pi_cycle_distance_pct"]),
        "ma200_gap_pct": ma200_gap,
        "ma350_gap_pct": ma350_gap,
        "return_365d": return_365d,
        "drawdown_from_ath_pct": drawdown,
        "reasons": reasons,
        "note": "현재 버전의 cycle score는 가격 기반 proxy이며 온체인/ETF 데이터는 미연결 상태입니다.",
    }
