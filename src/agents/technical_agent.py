import pandas as pd


def run_technical_agent(df: pd.DataFrame) -> dict:
    latest = df.dropna().iloc[-1]

    score = 50
    reasons: list[str] = []

    if latest["close"] > latest["ma200"]:
        score += 15
        reasons.append("가격이 MA200 위")
    else:
        score -= 15
        reasons.append("가격이 MA200 아래")

    if latest["ma200_slope_20d"] > 0:
        score += 10
        reasons.append("MA200 기울기 상승")
    else:
        score -= 10
        reasons.append("MA200 기울기 하락")

    if latest["ma20_slope_5d"] > 0:
        score += 8
        reasons.append("MA20 단기 추세 상승")
    else:
        score -= 8
        reasons.append("MA20 단기 추세 하락")

    if 45 <= latest["rsi14"] <= 65:
        score += 8
        reasons.append("RSI가 과열되지 않은 중립~강세 영역")
    elif latest["rsi14"] >= 75:
        score -= 10
        reasons.append("RSI 과열 부담")
    elif latest["rsi14"] <= 35:
        score += 5
        reasons.append("RSI 과매도 반등 가능 구간")

    if latest["volume_ratio"] >= 1.2 and latest["return_3d"] > 0:
        score += 7
        reasons.append("거래량을 동반한 단기 상승")

    score = max(0, min(100, score))

    if score >= 70:
        stance = "bullish"
    elif score <= 35:
        stance = "bearish"
    else:
        stance = "neutral"

    return {
        "stance": stance,
        "score": score,
        "reasons": reasons,
    }
