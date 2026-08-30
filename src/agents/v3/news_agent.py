from __future__ import annotations

import re

from src.agents.v3.expert_common import maybe_llm_interpret
from src.retrieval.text_retriever import retrieve_documents
from src.tools.research.news_search_tool import search_btc_news

POSITIVE = ["inflow", "buy", "approval", "reserve", "easing", "cut", "liquidity", "adoption", "rally", "surge"]
NEGATIVE = ["outflow", "ban", "hack", "sell", "lawsuit", "tightening", "hike", "crackdown", "liquidation", "drop"]


def _lexical_score(docs: list[dict]) -> float:
    score = 0
    for doc in docs:
        text = re.sub(r"[^a-z ]", " ", doc.get("title", "").lower())
        score += 4 * sum(word in text for word in POSITIVE)
        score -= 4 * sum(word in text for word in NEGATIVE)
    return max(-100.0, min(100.0, float(score)))


def run_news_agent(question: str, core_context: dict, raw: dict | None = None) -> dict:
    raw = raw or search_btc_news()
    if not raw.get("available"):
        return {
            "available": False, "score": 0.0, "confidence": 0.15, "summary": "News search unavailable.",
            "documents": [], "evidence": [], "risks": raw.get("errors", []), "raw": raw,
            "interpretation_source": "fallback",
        }
    query = f"{question} bitcoin BTC ETF dollar Fed regulation catalyst"
    docs = retrieve_documents(query, raw.get("documents", []), top_k=6)
    score = _lexical_score(docs)
    fallback = {
        "available": True,
        "score": score,
        "confidence": min(0.75, 0.35 + 0.06 * len(docs)),
        "summary": f"Retrieved {len(docs)} recent news items relevant to the research question.",
        "documents": docs,
        "evidence": [doc["title"] for doc in docs[:5]],
        "risks": ["Headline retrieval is not a substitute for reading full primary-source articles."],
        "raw": {k: v for k, v in raw.items() if k != "documents"},
        "interpretation_source": "fallback",
    }
    interpreted = maybe_llm_interpret("news", {"question": question, "core": core_context, "retrieved_documents": docs}, fallback)
    interpreted["documents"] = docs
    return interpreted
