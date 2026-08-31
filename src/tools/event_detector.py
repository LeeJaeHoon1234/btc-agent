from __future__ import annotations

import math


def _num(data: dict, key: str):
    try:
        x = float(data.get(key))
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def detect_market_events(live: dict, derivatives: dict | None = None) -> list[dict]:
    """Detect notable state changes. Thresholds only detect events; they do not dictate the final trade decision."""
    m = live.get("metrics", {}) if isinstance(live, dict) else {}
    events: list[dict] = []
    r15 = _num(m, "return_15m_pct")
    r1h = _num(m, "return_1h_pct")
    r4h = _num(m, "return_4h_pct")
    rebound = _num(m, "rebound_from_24h_low_pct") or _num(m, "rebound_from_recent_low_pct")
    pullback = _num(m, "pullback_from_24h_high_pct") or _num(m, "pullback_from_recent_high_pct")
    vz = _num(m, "volume_zscore")
    vr = _num(m, "volume_ratio")
    range_pos = _num(m, "position_in_24h_range")

    def add(event_id: str, kind: str, severity: int, title: str, facts: list[str], direction: int = 0):
        events.append({"id": event_id, "kind": kind, "severity": severity, "title": title, "facts": facts, "direction": max(-1, min(1, int(direction)))})

    if r15 is not None and abs(r15) >= 1.6:
        add("fast_shock", "shock", min(5, 2 + int(abs(r15) // 1.5)), "15분 급등" if r15 > 0 else "15분 급락", [f"15분 {r15:+.2f}%"], 1 if r15 > 0 else -1)
    if r1h is not None and abs(r1h) >= 3.0:
        add("hour_shock", "shock", min(5, 3 + int(abs(r1h) // 3)), "1시간 급등" if r1h > 0 else "1시간 급락", [f"1시간 {r1h:+.2f}%"], 1 if r1h > 0 else -1)
    if rebound is not None and rebound >= 3.0 and ((r1h or 0) > 0.7 or (r4h or 0) > 1.0):
        facts = [f"일중 저점 대비 {rebound:+.2f}%"]
        if r1h is not None: facts.append(f"최근 1시간 {r1h:+.2f}%")
        add("flush_rebound", "rebound", 4 if rebound >= 5 else 3, "급락 뒤 강한 반등", facts, 1)
    if pullback is not None and pullback <= -3.0 and ((r1h or 0) < -0.7 or (r4h or 0) < -1.0):
        add("high_rejection", "rejection", 3, "고점에서 빠르게 밀림", [f"일중 고점 대비 {pullback:.2f}%"], -1)
    if (vz is not None and vz >= 2.0) or (vr is not None and vr >= 2.0):
        facts = []
        if vz is not None: facts.append(f"거래량 z-score {vz:.1f}")
        if vr is not None: facts.append(f"최근 거래량 {vr:.1f}배")
        add("volume_spike", "volume", 3, "거래량 급증", facts)
    if range_pos is not None and range_pos >= 0.92 and (r1h or 0) > 0:
        add("near_high", "breakout", 2, "일중 고점권", [f"오늘 가격 범위 상단 {range_pos * 100:.0f}% 위치"], 1)

    d = derivatives or {}
    if d.get("available"):
        oi = _num(d, "open_interest_change_24h_pct")
        funding = _num(d, "funding_rate")
        if oi is not None and abs(oi) >= 7:
            add("oi_jump", "leverage", 3, "선물 포지션 급변", [f"미결제약정 24시간 {oi:+.1f}%"])
        if funding is not None and abs(funding) >= 0.0005:
            side = "롱" if funding > 0 else "숏"
            add("funding_crowding", "leverage", 3, f"{side} 쏠림 주의", [f"펀딩비 {funding * 100:+.4f}%"])

    # Most severe/currently informative events first; stable order within severity.
    return sorted(events, key=lambda x: x["severity"], reverse=True)[:6]
