from __future__ import annotations

from collections import defaultdict
from typing import Any

DOMAIN_MAP = {
    "price": "technical", "technical": "technical", "model": "historical",
    "derivatives": "derivatives", "onchain": "onchain_flow", "flow": "onchain_flow",
    "sentiment": "news", "macro": "macro", "news": "news",
}
# Macro and news are intentionally separate members.  Combining them under one
# card made the UI say “macro/news” while the council actually consumed only the
# macro specialist.  Independent cards make disagreement auditable.
COUNCIL_DOMAINS = ("technical", "derivatives", "onchain_flow", "macro", "news", "historical", "risk")


def _stance(score: float) -> str:
    if score >= 0.18: return "BULLISH"
    if score <= -0.18: return "BEARISH"
    return "NEUTRAL"


def _specialist_stance(view: dict | None, fallback_score: float) -> tuple[str, str]:
    """Prefer an explicit specialist judgment; use its score only if no label exists."""
    if view:
        explicit = str(view.get("stance") or "").upper()
        if explicit in {"BULLISH", "POSITIVE", "UPTREND"}:
            return "BULLISH", "independent_specialist"
        if explicit in {"BEARISH", "NEGATIVE", "DOWNTREND"}:
            return "BEARISH", "independent_specialist"
        if explicit in {"NEUTRAL", "CAUTION", "UNKNOWN"}:
            return "NEUTRAL", "independent_specialist"
        regime = str(view.get("regime") or "").upper()
        if any(token in regime for token in ("BEARISH", "RISK_OFF", "DOWNTREND")):
            return "BEARISH", "independent_specialist"
        if any(token in regime for token in ("BULLISH", "RISK_ON", "UPTREND")):
            return "BULLISH", "independent_specialist"
        try:
            domain_score = float(view.get("score")) / 100.0
            if abs(domain_score) >= 0.18:
                return _stance(domain_score), "independent_specialist"
            return "NEUTRAL", "independent_specialist"
        except (TypeError, ValueError):
            return "NEUTRAL", "independent_specialist"
    return _stance(fallback_score), "deterministic_domain_fallback"



def _ko_regime(value: str) -> str:
    mapping = {
        "HEALTHY_BULL": "건강한 상승 구조", "LEVERAGED_BULL": "레버리지 동반 상승",
        "SHORT_SQUEEZE": "숏 청산성 상승", "LONG_FLUSH": "롱 청산성 하락",
        "BEARISH_LEVERAGE": "하락 레버리지 확대", "RISK_ON_TAILWIND": "위험자산 우호",
        "RISK_OFF_HEADWIND": "위험자산 비우호", "NEUTRAL": "중립", "UNAVAILABLE": "데이터 부족",
    }
    return mapping.get(str(value or "").upper(), str(value or "").replace("_", " ").lower())


def _display_thesis(domain: str, view: dict | None, facts: list[dict], stance: str, language: str) -> str:
    view = view or {}
    if language != "ko":
        return str(view.get("summary") or (facts[0].get("simple") if facts else "No strong domain evidence available."))
    if domain == "technical":
        raw = view.get("raw_score")
        if raw is not None:
            label = {"BULLISH": "강세", "BEARISH": "약세", "NEUTRAL": "중립"}.get(stance, "중립")
            evidence = [str(x) for x in (view.get("evidence") or [])[:2]]
            suffix = f" 주요 근거: {' · '.join(evidence)}." if evidence else ""
            return f"기술 지표 종합은 {label}입니다. 기술 점수는 {float(raw):.0f}/100입니다.{suffix}"
    if domain == "derivatives":
        if view.get("available") is False:
            return "파생시장 데이터가 없어 OI·펀딩·포지셔닝을 확인할 수 없습니다. 이 영역은 강한 근거로 쓰지 않습니다."
        regime = _ko_regime(view.get("regime"))
        evidence = [str(x) for x in (view.get("evidence") or [])[:2]]
        suffix = f" ({' · '.join(evidence)})" if evidence else ""
        return f"파생시장 상태는 {regime}입니다.{suffix}"
    if domain == "macro":
        regime = _ko_regime(view.get("regime"))
        evidence = [str(x) for x in (view.get("evidence") or [])[:2]]
        if view:
            suffix = f" ({' · '.join(evidence)})" if evidence else ""
            return f"거시 환경은 {regime} 쪽입니다.{suffix}"
    if domain == "news":
        evidence = [str(x) for x in (view.get("evidence") or [])[:2]]
        if view.get("available") is False:
            return "최신 뉴스 데이터를 확인할 수 없어 방향 근거로 쓰지 않습니다."
        if evidence:
            return "최근 뉴스에서 주목한 항목: " + " · ".join(evidence) + "."
    if domain == "historical":
        raw = view.get("raw") or {}
        m7 = raw.get("median_forward_7d_pct")
        m30 = raw.get("median_forward_30d_pct")
        if m7 is not None or m30 is not None:
            parts = []
            if m7 is not None: parts.append(f"7일 중앙값 {float(m7):+.1f}%")
            if m30 is not None: parts.append(f"30일 중앙값 {float(m30):+.1f}%")
            return "과거 유사 구간은 " + ", ".join(parts) + "였습니다. 반복을 보장하는 근거는 아닙니다."
    if facts:
        return str(facts[0].get("simple") or facts[0].get("fact") or "현재 확인 가능한 근거가 제한적입니다.")
    return "현재 확인 가능한 근거가 부족합니다."


def _counterargument(domain: str, view: dict | None, stance: str, language: str) -> str:
    risks = [str(x).strip() for x in ((view or {}).get("risks") or []) if str(x).strip()]
    if risks:
        return risks[0][:280]
    if language != "ko":
        return "The view can change if the underlying evidence changes; unavailable inputs are not treated as neutral confirmation."
    messages = {
        "technical": "가격 구조가 바뀌거나 추세 지표가 꺾이면 기술적 판단도 빠르게 달라질 수 있습니다.",
        "derivatives": "OI·펀딩·청산 데이터가 바뀌거나 누락되면 파생시장 판단 신뢰도도 달라집니다.",
        "onchain_flow": "ETF·온체인 자금흐름은 일 단위로 갱신되므로 실시간 가격 움직임과 시차가 있습니다.",
        "macro": "거시는 BTC 방향을 단독으로 결정하지 않으며 가격 자체가 거시 역풍을 무시할 수도 있습니다.",
        "news": "헤드라인은 빠르게 바뀌고 중복·추측성 보도가 섞일 수 있어 단독 매매 근거로 쓰지 않습니다.",
        "historical": "유사한 과거 구간도 이후 결과 편차가 커 현재 장이 그대로 반복된다고 볼 수 없습니다.",
    }
    return messages.get(domain, "현재 근거가 바뀌면 이 판단도 달라질 수 있습니다.")

def build_agent_council(*, facts: list[dict], priors: dict[str, dict], forecasts: dict, market_state: dict,
                        data_health: dict, events: list[dict], specialist_views: dict | None = None, language: str = "ko") -> dict:
    """Create independent logical agent views without sharing a final score between domains.

    Existing specialist outputs are preserved, while deterministic priors are used only when a
    specialist has no opinion. Each member must expose both thesis and counter-case.
    """
    specialist_views = specialist_views or {}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for fact in facts or []:
        grouped[DOMAIN_MAP.get(str(fact.get("domain")), "historical")].append(fact)

    agents: dict[str, dict[str, Any]] = {}
    for domain in COUNCIL_DOMAINS:
        domain_facts = grouped.get(domain, [])
        weighted = 0.0; total = 0.0
        for fact in domain_facts:
            prior = priors.get(str(fact.get("id")), {})
            strength = float(prior.get("strength", 0.0) or 0.0)
            weighted += float(prior.get("direction", 0) or 0) * strength
            total += max(0.12, strength)
        score = weighted / total if total else 0.0

        source_view = specialist_views.get(domain)
        if source_view is None:
            # Map V3 specialists into V5 council names without merging independent domains.
            source_view = specialist_views.get({"macro": "macro", "news": "news", "historical": "historical", "technical": "technical", "derivatives": "derivatives"}.get(domain, ""))
        confidence = float((source_view or {}).get("confidence", 0.45) or 0.45)
        summary = str((source_view or {}).get("summary") or "")
        # Evidence ordering intentionally does not use bullish/bearish prior strength.
        # The analyst sees auditable raw facts in registry order; priors only rescue domains
        # that have no independent specialist judgment.
        evidence_ids = [str(x.get("id")) for x in domain_facts[:4]]
        stance, stance_source = _specialist_stance(source_view, score)
        thesis = _display_thesis(domain, source_view, domain_facts, stance, language)
        opposite = _counterargument(domain, source_view, stance, language)
        agents[domain] = {
            "stance": stance,
            "confidence": max(0.20, min(0.85, confidence)),
            "thesis": thesis[:360],
            "counterargument": opposite,
            "evidence_ids": evidence_ids,
            "fact_count": len(domain_facts),
            "available": (bool(source_view.get("available", True)) if source_view is not None else bool(domain_facts)),
            "source": stance_source,
        }

    # Risk is intentionally asymmetric and may veto an otherwise bullish council.
    unavailable = [k for k, v in (data_health or {}).items() if isinstance(v, dict) and v.get("status") != "ok"]
    severe_events = [e for e in events or [] if float(e.get("severity", 0) or 0) >= 4]
    q10_1w = ((forecasts or {}).get("1W") or {}).get("q10_return_pct")
    risk_score = 0
    risk_score += min(35, len(unavailable) * 6)
    risk_score += min(35, len(severe_events) * 18)
    if q10_1w is not None and float(q10_1w) <= -10: risk_score += 20
    acute = str((market_state or {}).get("acute_state") or "")
    if acute in {"volatility_shock_down", "bearish_leverage", "long_flush"}: risk_score += 15
    agents["risk"] = {
        "stance": "BEARISH" if risk_score >= 45 else "NEUTRAL",
        "confidence": min(0.90, 0.45 + risk_score / 180),
        "thesis": (f"리스크 압력은 {min(100, risk_score)}/100입니다. 데이터 품질·하방 꼬리위험·급변 이벤트를 함께 봅니다." if language == "ko" else f"Risk pressure score {min(100, risk_score)}/100 from data quality, tail risk and acute events."),
        "counterargument": ("데이터가 정상화되고 급변 이벤트가 해소되면 리스크 압력은 빠르게 낮아질 수 있습니다." if language == "ko" else "Risk pressure can fall quickly if data normalizes and the acute event resolves."),
        "evidence_ids": [],
        "fact_count": 0,
        "available": True,
        "risk_pressure": min(100, risk_score),
        "source": "risk_council_fallback",
    }

    directional = [a for k, a in agents.items() if k != "risk" and a.get("stance") in {"BULLISH", "BEARISH"}]
    bulls = sum(1 for a in directional if a["stance"] == "BULLISH")
    bears = sum(1 for a in directional if a["stance"] == "BEARISH")
    disagreement = 0.0 if not directional else 1.0 - abs(bulls - bears) / max(1, bulls + bears)
    return {
        "agents": agents,
        "bullish_members": bulls,
        "bearish_members": bears,
        "disagreement": round(disagreement, 3),
        "rule": "members are evaluated independently; no majority vote directly controls position size",
    }
