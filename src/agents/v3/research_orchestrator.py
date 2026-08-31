from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextvars import copy_context

from src.agents.v3.derivatives_agent import run_derivatives_agent
from src.agents.v3.historical_agent import run_historical_agent
from src.agents.v3.macro_agent import run_macro_agent
from src.agents.v3.news_agent import run_news_agent
from src.agents.v3.research_synthesizer import synthesize_research


def _demo_raw() -> dict:
    return {
        "derivatives": {
            "available": True,
            "provider": "demo",
            "funding_rate": 0.00012,
            "open_interest": 81234.0,
            "open_interest_change_24h_pct": -2.7,
            "global_long_short_ratio": 1.25,
            "top_trader_position_ratio": 1.42,
            "taker_buy_sell_ratio": 1.08,
        },
        "macro": {
            "available": True,
            "provider": "demo",
            "dollar_index": 99.2,
            "dollar_change_window_pct": -0.6,
            "us10y_yield": 3.91,
            "us10y_change_window_pct": -1.4,
        },
        "news": {
            "available": True,
            "provider": "demo",
            "documents": [
                {"title": "Bitcoin ETF demand improves while dollar softens", "url": "https://example.com/demo-1", "source": "Demo News", "published_at": None, "text": "Bitcoin ETF demand improves dollar softens institutional inflow"},
                {"title": "Traders watch leverage after BTC rebound", "url": "https://example.com/demo-2", "source": "Demo News", "published_at": None, "text": "BTC leverage funding open interest rebound traders"},
            ],
            "errors": [],
        },
    }


def _technical_expert(core_context: dict) -> dict:
    technical = core_context.get("technical", {})
    stance = technical.get("stance", "neutral")
    raw_score = float(technical.get("score", 50))
    score = max(-100.0, min(100.0, (raw_score - 50) * 2))
    return {
        "available": True,
        "score": score,
        "confidence": 0.75,
        "summary": f"Technical stance is {stance} with score {raw_score:.1f}/100.",
        "evidence": technical.get("reasons", [])[:6],
        "risks": [],
        "interpretation_source": "core",
    }


def run_research(question: str, plan: dict, state, source: str = "live", raw_inputs: dict | None = None, synthesis_llm: bool = True) -> tuple[dict, dict]:
    selected = set(plan.get("selected_skills", []))
    core = state.compact_context()
    demo = _demo_raw() if source == "demo" else {}
    supplied = raw_inputs or {}
    experts: dict = {}

    if "technical" in selected:
        experts["technical"] = _technical_expert(core)

    jobs = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        if "derivatives" in selected:
            ctx = copy_context()
            jobs[pool.submit(ctx.run, run_derivatives_agent, core, supplied.get("derivatives", demo.get("derivatives")))] = "derivatives"
        if "macro" in selected:
            ctx = copy_context()
            jobs[pool.submit(ctx.run, run_macro_agent, core, supplied.get("macro", demo.get("macro")))] = "macro"
        if "news" in selected:
            ctx = copy_context()
            jobs[pool.submit(ctx.run, run_news_agent, question, core, supplied.get("news", demo.get("news")))] = "news"
        if "historical" in selected:
            ctx = copy_context()
            jobs[pool.submit(ctx.run, run_historical_agent, state.market_df, core)] = "historical"

        for future in as_completed(jobs):
            name = jobs[future]
            try:
                experts[name] = future.result()
            except Exception as exc:
                experts[name] = {
                    "available": False,
                    "score": 0.0,
                    "confidence": 0.1,
                    "summary": f"{name} specialist failed safely.",
                    "evidence": [],
                    "risks": [str(exc)],
                }

    synthesis = synthesize_research(question, plan, experts, use_llm=synthesis_llm)
    return experts, synthesis


def collect_evidence(experts: dict) -> list[dict]:
    items: list[dict] = []
    counter = 1
    for agent, result in experts.items():
        if not isinstance(result, dict):
            continue
        if agent == "news":
            for doc in result.get("documents", [])[:8]:
                items.append({
                    "id": f"E{counter}",
                    "agent": agent,
                    "kind": "source",
                    "title": doc.get("title"),
                    "claim": doc.get("title"),
                    "url": doc.get("url"),
                    "source": doc.get("source"),
                    "published_at": doc.get("published_at"),
                    "confidence": result.get("confidence"),
                })
                counter += 1
        else:
            for claim in result.get("evidence", [])[:6]:
                items.append({
                    "id": f"E{counter}",
                    "agent": agent,
                    "kind": "derived",
                    "title": f"{agent} evidence",
                    "claim": str(claim),
                    "url": None,
                    "source": result.get("raw", {}).get("provider") if isinstance(result.get("raw"), dict) else None,
                    "published_at": None,
                    "confidence": result.get("confidence"),
                })
                counter += 1
    return items
