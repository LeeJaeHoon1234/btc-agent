from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Literal

from src.agents.llm_client import llm_configured
from src.core.orchestrator import BTCAgentOrchestrator
from src.core.v3.usage_guard import llm_budget_context, usage_guard
from src.tools.demo_data import make_demo_market_data

SourceMode = Literal["live", "demo"]


@dataclass
class CacheEntry:
    created_at: float
    state: object
    llm_usage: dict


class AnalysisService:
    """Runs BTC Agent V3.1 with cache-aware LLM quota fallback."""

    def __init__(self) -> None:
        self.ttl_seconds = int(os.getenv("ANALYSIS_CACHE_TTL_SECONDS", "300"))
        self._cache: dict[tuple[str, int, str, str], CacheEntry] = {}
        self._lock = threading.Lock()

    def analyze(
        self,
        market: str,
        history_years: int,
        source: SourceMode = "live",
        question: str = "",
        client_key: str = "anonymous",
    ):
        normalized_question = " ".join((question or "").split()).strip().lower()
        key = (market, history_years, source, normalized_question)
        now = time.monotonic()

        if source == "live":
            with self._lock:
                cached = self._cache.get(key)
                if cached and now - cached.created_at <= self.ttl_seconds:
                    cached_usage = dict(cached.llm_usage)
                    cached_usage["mode"] = "cache"
                    cached_usage["reason"] = "cache_hit_no_new_llm_cost"
                    cached_usage["calls_used"] = 0
                    cached_usage["input_tokens"] = 0
                    cached_usage["output_tokens"] = 0
                    cached_usage["total_tokens"] = 0
                    return cached.state, True, cached_usage

        reservation = usage_guard.reserve_llm_analysis(
            client_key,
            llm_configured=llm_configured(),
        )

        orchestrator = BTCAgentOrchestrator(market=market, history_years=history_years)
        with llm_budget_context(allowed=reservation.allowed, reason=reservation.reason) as budget:
            if source == "demo":
                market_df = make_demo_market_data(days=max(450, history_years * 365))
                state = orchestrator.run(market_df=market_df, question=question, source=source)
            else:
                state = orchestrator.run(question=question, source=source)

        budget_snapshot = budget.snapshot()
        if reservation.reserved and budget_snapshot["calls_used"] == 0:
            usage_guard.release_llm_reservation(client_key, reservation)

        quota = usage_guard.status(client_key)
        llm_usage = {
            **budget_snapshot,
            "mode": "llm" if budget_snapshot["calls_used"] > 0 else "fallback",
            "reason": budget_snapshot.get("reason") or reservation.reason,
            "quota": quota,
        }

        if source == "live":
            with self._lock:
                self._cache[key] = CacheEntry(created_at=now, state=state, llm_usage=llm_usage)

        return state, False, llm_usage


analysis_service = AnalysisService()
