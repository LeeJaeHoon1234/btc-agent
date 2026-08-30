from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Literal

from src.core.orchestrator import BTCAgentOrchestrator
from src.tools.demo_data import make_demo_market_data

SourceMode = Literal["live", "demo"]


@dataclass
class CacheEntry:
    created_at: float
    state: object


class AnalysisService:
    """Runs BTC Agent V3 and briefly caches identical live research requests."""

    def __init__(self) -> None:
        self.ttl_seconds = int(os.getenv("ANALYSIS_CACHE_TTL_SECONDS", "300"))
        self._cache: dict[tuple[str, int, str, str], CacheEntry] = {}
        self._lock = threading.Lock()

    def analyze(self, market: str, history_years: int, source: SourceMode = "live", question: str = ""):
        normalized_question = " ".join((question or "").split()).strip().lower()
        key = (market, history_years, source, normalized_question)
        now = time.monotonic()

        if source == "live":
            with self._lock:
                cached = self._cache.get(key)
                if cached and now - cached.created_at <= self.ttl_seconds:
                    return cached.state, True

        orchestrator = BTCAgentOrchestrator(market=market, history_years=history_years)

        if source == "demo":
            market_df = make_demo_market_data(days=max(450, history_years * 365))
            state = orchestrator.run(market_df=market_df, question=question, source=source)
        else:
            state = orchestrator.run(question=question, source=source)

        if source == "live":
            with self._lock:
                self._cache[key] = CacheEntry(created_at=now, state=state)

        return state, False


analysis_service = AnalysisService()
