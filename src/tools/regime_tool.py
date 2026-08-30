import pandas as pd


def detect_regime(df: pd.DataFrame) -> dict:
    latest = df.dropna(subset=["ma20", "ma60", "ma200", "ma200_slope_20d"]).iloc[-1]

    close = float(latest["close"])
    ma20 = float(latest["ma20"])
    ma60 = float(latest["ma60"])
    ma200 = float(latest["ma200"])
    ma200_slope = float(latest["ma200_slope_20d"])

    reasons: list[str] = []

    if close > ma20 > ma60 > ma200 and ma200_slope > 0:
        regime = "bull_trend"
        score = 90
        reasons.append("가격과 단기/중기/장기 이동평균이 정배열")
        reasons.append("MA200 기울기가 양수")
    elif close < ma20 < ma60 < ma200 and ma200_slope < 0:
        regime = "bear_trend"
        score = 10
        reasons.append("가격과 이동평균이 역배열")
        reasons.append("MA200 기울기가 음수")
    elif close > ma200 and ma200_slope >= 0:
        regime = "bull_transition"
        score = 68
        reasons.append("가격이 MA200 위에 있고 장기 추세가 개선 중")
    elif close < ma200 and ma200_slope <= 0:
        regime = "bear_transition"
        score = 32
        reasons.append("가격이 MA200 아래이고 장기 추세가 약함")
    else:
        regime = "sideways"
        score = 50
        reasons.append("단기와 장기 추세가 서로 충돌")

    return {
        "regime": regime,
        "bull_score": score,
        "reasons": reasons,
    }
