from __future__ import annotations

import math
from typing import Any

HORIZONS = ("NOW", "TODAY", "1W", "1M", "1Y")


def _f(value, default=None):
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _signal(signal_id: str, domain: str, horizons: list[str], direction: int, strength: float, fact: str, simple: str, value=None, freshness: str = "") -> dict:
    return {
        "id": signal_id,
        "domain": domain,
        "horizons": horizons,
        "direction": max(-1, min(1, int(direction))),
        "strength": max(0.0, min(1.0, float(strength))),
        "fact": fact,
        "simple": simple,
        "value": value,
        "freshness": freshness,
    }


def build_signal_registry(state) -> list[dict]:
    """Convert facts into auditable evidence candidates.

    Direction/strength are broad priors for deterministic fallback only. The LLM may choose
    which facts matter most and may disagree, but it must cite signal IDs and cannot alter values.
    """
    signals: list[dict] = []
    live = state.live or {}
    m = live.get("metrics", {})
    latest = state.latest or {}
    deriv = ((state.experts or {}).get("derivatives") or {}).get("raw", {})
    macro = ((state.experts or {}).get("macro") or {}).get("raw", {})
    flow = (state.external or {}).get("flow", {})
    sentiment = (state.external or {}).get("sentiment", {})
    onchain = (state.external or {}).get("onchain", {})

    r15, r1h, r4h, r24 = [_f(m.get(k)) for k in ("return_15m_pct", "return_1h_pct", "return_4h_pct", "return_24h_pct")]
    for sid, val, hs, label in [
        ("S_NOW_15M", r15, ["NOW"], "15분"), ("S_NOW_1H", r1h, ["NOW", "TODAY"], "1시간"),
        ("S_TODAY_4H", r4h, ["NOW", "TODAY"], "4시간"), ("S_TODAY_24H", r24, ["TODAY", "1W"], "24시간"),
    ]:
        if val is not None:
            direction = 1 if val > 0.25 else -1 if val < -0.25 else 0
            signals.append(_signal(sid, "price", hs, direction, min(1, abs(val) / 4), f"{label} 수익률 {val:+.2f}%", f"{label} 가격이 {'오르고' if val > 0 else '내리고' if val < 0 else '거의 변하지 않고'} 있습니다.", val, "live"))

    rebound = _f(m.get("rebound_from_24h_low_pct"))
    pullback = _f(m.get("pullback_from_24h_high_pct"))
    if rebound is not None:
        signals.append(_signal("S_REBOUND", "price", ["NOW", "TODAY"], 1 if rebound >= 2 else 0, min(1, rebound / 7), f"24시간 저점 대비 {rebound:+.2f}%", f"오늘 저점에서 {rebound:.1f}% 반등했습니다.", rebound, "live"))
    if pullback is not None:
        signals.append(_signal("S_HIGH_GAP", "price", ["NOW", "TODAY"], -1 if pullback <= -3 else 1 if pullback >= -0.8 else 0, min(1, abs(pullback) / 6), f"24시간 고점 대비 {pullback:.2f}%", f"오늘 고점과의 거리는 {abs(pullback):.1f}%입니다.", pullback, "live"))

    for key, sid, simple_name, hs in [
        ("rsi14", "S_RSI_FAST", "단기 상승 속도", ["NOW", "TODAY"]),
        ("vwap_gap_pct", "S_VWAP", "최근 평균 체결 가격과의 거리", ["NOW", "TODAY"]),
        ("volume_ratio", "S_VOLUME", "최근 거래량", ["NOW", "TODAY", "1W"]),
        ("volume_zscore", "S_VOLUME_SPIKE", "거래량 급증 정도", ["NOW", "TODAY"]),
        ("orderbook_imbalance", "S_BOOK", "호가 매수·매도 균형", ["NOW"]),
        ("spot_taker_buy_sell_ratio", "S_TAKER_SPOT", "실제 체결 매수·매도 비율", ["NOW", "TODAY"]),
        ("atr14_pct", "S_ATR", "단기 변동 폭", ["NOW", "TODAY"]),
    ]:
        val = _f(m.get(key))
        if val is None: continue
        direction, strength = 0, 0.35
        if key == "rsi14":
            direction = 1 if 52 <= val <= 68 else -1 if val >= 78 or val <= 35 else 0; strength = min(1, abs(val - 50) / 35)
        elif key == "vwap_gap_pct":
            direction = 1 if 0 < val < 3 else -1 if val > 5 or val < -3 else 0; strength = min(1, abs(val) / 6)
        elif key == "volume_ratio":
            direction = 1 if val >= 1.15 else 0; strength = min(1, abs(val - 1))
        elif key == "volume_zscore":
            strength = min(1, abs(val) / 3); direction = 0
        elif key == "orderbook_imbalance":
            direction = 1 if val > .08 else -1 if val < -.08 else 0; strength = min(1, abs(val) * 3)
        elif key == "spot_taker_buy_sell_ratio":
            direction = 1 if val > 1.05 else -1 if val < .95 else 0; strength = min(1, abs(val - 1) * 2)
        fact = f"{simple_name}: {val:.3f}" if abs(val) < 10 else f"{simple_name}: {val:.1f}"
        signals.append(_signal(sid, "microstructure", hs, direction, strength, fact, fact, val, "live"))

    # Daily / slow facts
    daily_specs = [
        ("rsi14", "S_D_RSI", ["1W", "1M"], "일봉 RSI"),
        ("ma20_gap_pct", "S_MA20_GAP", ["1W", "1M"], "20일 평균과의 거리"),
        ("ma20_slope_5d", "S_MA20_SLOPE", ["1W", "1M"], "20일 평균선 방향"),
        ("ma200_gap_pct", "S_MA200_GAP", ["1M", "1Y"], "200일 평균과의 거리"),
        ("ma200_slope_20d", "S_MA200_SLOPE", ["1M", "1Y"], "200일 평균선 방향"),
        ("return_7d", "S_RET_7D", ["1W"], "7일 수익률"),
        ("return_30d", "S_RET_30D", ["1M"], "30일 수익률"),
        ("return_365d", "S_RET_1Y", ["1Y"], "1년 수익률"),
        ("drawdown_from_ath_pct", "S_DD_ATH", ["1M", "1Y"], "사상 최고가 대비 거리"),
        ("volatility_30d_pct", "S_VOL_30D", ["1W", "1M"], "30일 변동성"),
    ]
    for key, sid, hs, label in daily_specs:
        val = _f(latest.get(key))
        if val is None: continue
        direction, strength = 0, min(1, abs(val) / 20)
        if key == "rsi14": direction = 1 if 52 <= val <= 68 else -1 if val >= 78 or val <= 35 else 0; strength = min(1, abs(val - 50) / 35)
        elif "slope" in key: direction = 1 if val > 0 else -1 if val < 0 else 0; strength = min(1, abs(val) / 5)
        elif "gap" in key and "ma200" in key: direction = 1 if val > 0 else -1; strength = min(1, abs(val) / 15)
        elif key in {"return_7d", "return_30d", "return_365d"}: direction = 1 if val > 0 else -1 if val < 0 else 0
        signals.append(_signal(sid, "technical", hs, direction, strength, f"{label} {val:+.2f}{'%' if key != 'rsi14' else ''}", f"{label}은 {val:+.1f}{'%' if key != 'rsi14' else ''}입니다.", val, "daily"))

    # Additional daily technical context (computed broadly; selected per horizon by the analyst).
    extra_specs = [
        ("macd_hist", "S_D_MACD", ["1W", "1M"], "MACD 변화", 0.0),
        ("adx14", "S_D_ADX", ["1W", "1M"], "추세 강도", 20.0),
        ("bb_position", "S_D_BB", ["1W", "1M"], "가격의 밴드 내 위치", 0.5),
        ("atr14_pct", "S_D_ATR", ["1W", "1M"], "일봉 평균 변동폭", 0.0),
        ("stoch_k", "S_D_STOCH", ["1W"], "단기 모멘텀 위치", 50.0),
        ("volume_zscore_30d", "S_D_VOLZ", ["1W", "1M"], "일봉 거래량 이상치", 0.0),
        ("obv_slope_10d", "S_D_OBV", ["1W", "1M"], "누적 거래량 방향", 0.0),
    ]
    for key, sid, hs, label, neutral in extra_specs:
        val = _f(latest.get(key))
        if val is None: continue
        direction, strength = 0, .35
        if key == "macd_hist": direction = 1 if val > 0 else -1 if val < 0 else 0; strength = .5
        elif key == "adx14": direction = 0; strength = min(1, max(0, val - 15) / 30)
        elif key == "bb_position": direction = -1 if val > 1.05 else 1 if .45 <= val <= .8 else 0; strength = min(1, abs(val - .5))
        elif key == "stoch_k": direction = -1 if val > 85 else 1 if 35 <= val <= 70 else 0; strength = min(1, abs(val - 50) / 45)
        elif key in {"volume_zscore_30d", "obv_slope_10d"}: direction = 1 if val > 0.3 else -1 if val < -0.3 else 0; strength = min(1, abs(val) / 3)
        signals.append(_signal(sid, "technical", hs, direction, strength, f"{label}: {val:.3f}", f"{label}은 {val:.2f}입니다.", val, "daily"))

    ml = state.ml or {}
    if ml.get("available") and _f(ml.get("up_probability")) is not None:
        p = _f(ml.get("up_probability"))
        auc = _f((ml.get("metadata") or {}).get("walk_forward_mean_auc"))
        reliability = 0.25 if auc is not None and auc < .57 else .45
        signals.append(_signal("S_ML_30D", "model", ["1M"], 1 if p >= 57 else -1 if p <= 43 else 0, reliability, f"30일 ML 상승확률 {p:.1f}% / walk-forward AUC {auc if auc is not None else 'unknown'}", "30일 AI 예측은 참고 신호로만 사용합니다.", p, "daily"))

    if deriv.get("available"):
        for key, sid, label, hs in [
            ("funding_rate", "S_FUNDING", "선물 펀딩비", ["NOW", "TODAY", "1W"]),
            ("open_interest_change_24h_pct", "S_OI", "미결제약정 24시간 변화", ["NOW", "TODAY", "1W"]),
            ("taker_buy_sell_ratio", "S_TAKER_FUT", "선물 공격적 매수·매도", ["NOW", "TODAY"]),
            ("basis_rate", "S_BASIS", "선물 베이시스", ["TODAY", "1W"]),
        ]:
            val = _f(deriv.get(key))
            if val is None: continue
            direction, strength = 0, .45
            if key == "funding_rate": direction = -1 if val > .0005 else 1 if val < -.0003 else 0; strength = min(1, abs(val) / .001)
            elif key == "open_interest_change_24h_pct": strength = min(1, abs(val) / 12); direction = 0
            elif key == "taker_buy_sell_ratio": direction = 1 if val > 1.05 else -1 if val < .95 else 0; strength = min(1, abs(val - 1) * 2)
            factval = val * 100 if key == "funding_rate" else val
            suffix = "%" if key in {"funding_rate", "open_interest_change_24h_pct", "basis_rate"} else ""
            signals.append(_signal(sid, "derivatives", hs, direction, strength, f"{label} {factval:+.3f}{suffix}", f"{label}은 {factval:+.2f}{suffix}입니다.", val, "minutes"))

    if macro.get("available"):
        dxy = _f(macro.get("dollar_change_window_pct")); y10 = _f(macro.get("us10y_change_window_pct"))
        if dxy is not None: signals.append(_signal("S_DXY", "macro", ["1W", "1M"], -1 if dxy > 0 else 1, min(1, abs(dxy) / 2), f"달러지수 최근 변화 {dxy:+.2f}%", f"달러가 최근 {abs(dxy):.1f}% {'강해졌습니다' if dxy > 0 else '약해졌습니다'}.", dxy, "hours/daily"))
        if y10 is not None: signals.append(_signal("S_US10Y", "macro", ["1W", "1M"], -1 if y10 > 0 else 1, min(1, abs(y10) / 4), f"미 10년물 최근 변화 {y10:+.2f}%", f"미국 장기금리가 최근 {'올랐습니다' if y10 > 0 else '내렸습니다'}.", y10, "hours/daily"))

    if flow.get("available") and _f(flow.get("latest_total_musd")) is not None:
        val = _f(flow.get("latest_total_musd")); five = _f(flow.get("five_session_total_musd"))
        direction = 1 if val > 0 else -1 if val < 0 else 0
        signals.append(_signal("S_ETF_FLOW", "flow", ["TODAY", "1W", "1M"], direction, min(1, abs(val) / 800), f"미국 현물 ETF 최신 순유입 {val:+.1f}M USD / 5세션 {five:+.1f}M USD" if five is not None else f"미국 현물 ETF 최신 순유입 {val:+.1f}M USD", f"미국 현물 ETF 자금은 최신 세션에서 {val:+.0f}M달러입니다.", val, "daily"))

    if sentiment.get("available") and _f(sentiment.get("value")) is not None:
        val = _f(sentiment.get("value")); direction = -1 if val >= 80 else 1 if val <= 25 else 0
        signals.append(_signal("S_SENTIMENT", "sentiment", ["TODAY", "1W", "1M"], direction, min(1, abs(val - 50) / 45), f"Fear & Greed {val:.0f} ({sentiment.get('classification')})", f"시장 심리 지수는 {val:.0f}입니다.", val, "daily"))

    if onchain.get("available"):
        fee = _f(onchain.get("fee_fastest_sat_vb"))
        if fee is not None:
            signals.append(_signal("S_NETWORK_FEE", "onchain", ["1W", "1M"], 0, min(1, fee / 100), f"Bitcoin 빠른 전송 수수료 {fee:.0f} sat/vB", f"비트코인 네트워크 수수료는 {fee:.0f} sat/vB입니다.", fee, "minutes"))

    # Recent news is evidence but sentiment is intentionally left for LLM interpretation.
    news = (state.experts or {}).get("news", {})
    for i, doc in enumerate((news.get("documents") or [])[:5], start=1):
        title = str(doc.get("title", "")).strip()
        if title:
            signals.append(_signal(f"S_NEWS_{i}", "news", ["NOW", "TODAY", "1W"], 0, .45, title, title, title, "recent"))
    return signals


def _fallback_horizon(horizon: str, signals: list[dict], events: list[dict]) -> dict:
    relevant = [s for s in signals if horizon in s.get("horizons", [])]
    weighted = sum(s["direction"] * s["strength"] for s in relevant)
    total = sum(max(.15, s["strength"]) for s in relevant) or 1
    score = weighted / total
    if score >= .18: stance = "POSITIVE"
    elif score <= -.18: stance = "NEGATIVE"
    else: stance = "CAUTION" if any(e.get("severity", 0) >= 3 for e in events) and horizon in {"NOW", "TODAY"} else "NEUTRAL"
    ranked = sorted(relevant, key=lambda s: s["strength"], reverse=True)[:4]
    headline_map = {
        "POSITIVE": "상승 쪽 신호가 조금 더 많습니다.",
        "NEGATIVE": "하락 위험 신호가 조금 더 강합니다.",
        "CAUTION": "움직임이 커서 지금은 확인이 더 필요합니다.",
        "NEUTRAL": "방향 신호가 엇갈립니다.",
    }
    return {
        "horizon": horizon,
        "stance": stance,
        "confidence": round(min(.78, .42 + abs(score) * .45 + min(len(relevant), 8) * .015), 2),
        "headline": headline_map[stance],
        "summary": " ".join(s["simple"] for s in ranked[:2]) or "확인 가능한 데이터가 충분하지 않습니다.",
        "key_signal_ids": [s["id"] for s in ranked[:4]],
        "good": [s["simple"] for s in ranked if s["direction"] > 0][:2],
        "risks": [s["simple"] for s in ranked if s["direction"] < 0][:2],
        "source": "deterministic_fallback",
    }


def build_horizon_fallbacks(signals: list[dict], events: list[dict]) -> dict[str, dict]:
    return {h: _fallback_horizon(h, signals, events) for h in HORIZONS}
