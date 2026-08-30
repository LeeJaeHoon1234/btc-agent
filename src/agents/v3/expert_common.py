from __future__ import annotations

from typing import Any

from src.agents.llm_client import call_json_agent, llm_available
from src.core.v3.skill_registry import skill_registry
from config.settings import USE_SPECIALIST_LLM


def maybe_llm_interpret(skill_name: str, payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    if not llm_available() or not USE_SPECIALIST_LLM:
        return fallback
    skill = skill_registry.get(skill_name)
    instruction = f"""
You are operating under the following specialist skill definition.

{skill.content}

Analyze only the supplied tool output and core market context.
Do not invent missing data. If a field is unavailable, say so.
Return JSON only with these keys:
{{
  "summary": "one concise paragraph",
  "score": -100 to 100,
  "confidence": 0.0 to 1.0,
  "evidence": ["short evidence statements"],
  "risks": ["short risk statements"]
}}
"""
    try:
        result = call_json_agent(instruction, payload)
        score = max(-100.0, min(100.0, float(result.get("score", fallback.get("score", 0)))))
        confidence = max(0.0, min(1.0, float(result.get("confidence", fallback.get("confidence", 0.5)))))
        return fallback | {
            "summary": str(result.get("summary", fallback.get("summary", ""))),
            "score": score,
            "confidence": confidence,
            "evidence": list(result.get("evidence", fallback.get("evidence", [])))[:8],
            "risks": list(result.get("risks", fallback.get("risks", [])))[:8],
            "interpretation_source": "llm",
        }
    except Exception as exc:
        return fallback | {"llm_error": str(exc), "interpretation_source": "fallback"}
