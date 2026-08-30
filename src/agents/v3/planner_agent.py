from __future__ import annotations

from src.agents.llm_client import call_json_agent, llm_available
from src.core.v3.skill_registry import SkillRegistry, skill_registry

DEFAULT_QUESTION = "Should I add, hold, take profit, or reduce BTC now, and what evidence matters most?"


def _fallback_plan(question: str, registry: SkillRegistry) -> dict:
    q = question.lower()
    selected = ["technical", "risk"]

    keyword_map = {
        "derivatives": ["funding", "oi", "open interest", "long", "short", "squeeze", "청산", "롱", "숏", "펀딩"],
        "macro": ["dxy", "dollar", "fed", "yield", "cpi", "macro", "달러", "금리", "연준", "유동성"],
        "news": ["news", "why", "catalyst", "etf", "clarity", "trump", "뉴스", "호재", "악재", "왜", "재료"],
        "historical": ["history", "similar", "past", "cycle", "과거", "유사", "사이클"],
    }
    for skill, words in keyword_map.items():
        if any(word in q for word in words):
            selected.append(skill)

    # An open-ended autonomous decision should research broadly.
    if len(selected) <= 2 or any(word in q for word in ["add", "hold", "profit", "reduce", "buy", "sell", "추매", "익절", "손절", "매수"]):
        selected.extend(["derivatives", "macro", "news", "historical"])

    valid = set(registry.names())
    selected = list(dict.fromkeys(s for s in selected if s in valid))
    return {
        "objective": question or DEFAULT_QUESTION,
        "selected_skills": selected,
        "reason": "Heuristic planner selected broad evidence for an investment-decision query.",
        "source": "fallback",
    }


def make_research_plan(question: str | None, registry: SkillRegistry = skill_registry) -> dict:
    question = (question or DEFAULT_QUESTION).strip()
    fallback = _fallback_plan(question, registry)
    if not llm_available():
        return fallback

    instruction = f"""
You are the planning layer of a BTC research agent.
Choose only the specialist skills needed to answer the user's question.
Do not perform market analysis yourself. Do not invent data.
Available skills:
{registry.prompt_catalog()}

Return JSON only:
{{
  "objective": "...",
  "selected_skills": ["technical", "derivatives", "macro", "news", "historical", "risk"],
  "reason": "short routing rationale"
}}
"""
    try:
        result = call_json_agent(instruction, {"question": question})
        valid = set(registry.names())
        selected = [str(x) for x in result.get("selected_skills", []) if str(x) in valid]
        if not selected:
            return fallback
        if "risk" not in selected:
            selected.append("risk")
        return {
            "objective": str(result.get("objective", question)),
            "selected_skills": list(dict.fromkeys(selected)),
            "reason": str(result.get("reason", "LLM planner routing")),
            "source": "llm",
        }
    except Exception:
        return fallback
