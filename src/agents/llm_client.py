import json
import os
import re
from typing import Any

from config.settings import OPENAI_MODEL, USE_LLM
from src.core.v3.usage_guard import current_llm_budget, request_llm_enabled


def llm_configured() -> bool:
    """Whether the backend is globally configured to use OpenAI."""
    return USE_LLM and bool(os.getenv("OPENAI_API_KEY"))


def llm_available() -> bool:
    """Whether LLM use is allowed globally and for the current request budget."""
    return llm_configured() and request_llm_enabled()


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("LLM 응답에서 JSON 객체를 찾지 못했습니다.")

    return json.loads(match.group(0))


def _record_usage(response) -> None:
    budget = current_llm_budget()
    if budget is None:
        return
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    budget.record_tokens(
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        total_tokens=getattr(usage, "total_tokens", 0) or 0,
    )


def call_json_agent(system_instruction: str, payload: dict) -> dict[str, Any]:
    if not llm_configured():
        raise RuntimeError("OPENAI_API_KEY가 없거나 USE_LLM=false 입니다.")

    budget = current_llm_budget()
    if budget is not None:
        budget.authorize_call()

    from openai import OpenAI

    client = OpenAI()

    prompt = f"""
{system_instruction}

아래 입력은 Python이 계산한 사실 데이터다.
수치를 임의로 바꾸거나 새로 만들어내지 마라.
반드시 JSON object 하나만 반환하라. Markdown code fence를 쓰지 마라.

INPUT:
{json.dumps(payload, ensure_ascii=False, default=str, indent=2)}
"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
    )
    _record_usage(response)

    return _extract_json(response.output_text)
