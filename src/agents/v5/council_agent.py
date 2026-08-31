from __future__ import annotations

from collections import defaultdict
from typing import Any

DOMAIN_MAP = {
    "price": "technical", "technical": "technical", "model": "historical",
    "derivatives": "derivatives", "onchain": "onchain_flow", "flow": "onchain_flow",
    "sentiment": "macro_news", "macro": "macro_news", "news": "macro_news",
}
COUNCIL_DOMAINS = ("technical", "derivatives", "onchain_flow", "macro_news", "historical", "risk")


def _stance(score: float) -> str:
    if score >= 0.18: return "BULLISH"
    if score <= -0.18: return "BEARISH"
    return "NEUTRAL"


def _specialist_stance(view: dict | None, fallback_score: float) -> tuple[str, str]:
    """Prefer the specialist's own judgment; use deterministic priors only as fallback."""
    if view:
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


def build_agent_council(*, facts: list[dict], priors: dict[str, dict], forecasts: dict, market_state: dict,
                        data_health: dict, events: list[dict], specialist_views: dict | None = None) -> dict:
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
            # Map V3 specialists into V5 council names.
            source_view = specialist_views.get({"macro_news": "macro", "historical": "historical", "technical": "technical", "derivatives": "derivatives"}.get(domain, ""))
        confidence = float((source_view or {}).get("confidence", 0.45) or 0.45)
        summary = str((source_view or {}).get("summary") or "")
        # Evidence ordering intentionally does not use bullish/bearish prior strength.
        # The analyst sees auditable raw facts in registry order; priors only rescue domains
        # that have no independent specialist judgment.
        evidence_ids = [str(x.get("id")) for x in domain_facts[:4]]
        thesis = summary or (str(domain_facts[0].get("simple")) if domain_facts else "No strong domain evidence available.")
        opposite = "Evidence is mixed or could reverse if the cited facts change."
        stance, stance_source = _specialist_stance(source_view, score)
        agents[domain] = {
            "stance": stance,
            "confidence": max(0.20, min(0.85, confidence)),
            "thesis": thesis[:360],
            "counterargument": opposite,
            "evidence_ids": evidence_ids,
            "fact_count": len(domain_facts),
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
        "thesis": f"Risk pressure score {min(100, risk_score)}/100 from data quality, tail risk and acute events.",
        "counterargument": "Risk pressure can fall quickly if data normalizes and the acute event resolves.",
        "evidence_ids": [],
        "fact_count": 0,
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
