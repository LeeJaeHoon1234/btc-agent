from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Literal

from config.settings import ANALYSIS_CACHE_TTL_SECONDS, LIVE_SNAPSHOT_CACHE_TTL_SECONDS
from src.agents.llm_client import llm_configured
from src.core.orchestrator import BTCAgentOrchestrator
from src.core.v3.usage_guard import llm_budget_context, usage_guard
from src.tools.demo_data import make_demo_market_data
from src.tools.live_market import fetch_live_market_snapshot, make_demo_live_snapshot
from src.tools.event_detector import detect_market_events

SourceMode = Literal["live", "demo"]


@dataclass
class CacheEntry:
    created_at: float
    state: object
    llm_usage: dict


class LiveSnapshotService:
    """Cheap V4 fast-layer cache. No LLM calls."""
    def __init__(self) -> None:
        self.ttl_seconds = LIVE_SNAPSHOT_CACHE_TTL_SECONDS
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()

    def get(self, market: str = "KRW-BTC", source: SourceMode = "live") -> tuple[dict, bool]:
        key = f"{source}:{market}"
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(key)
            if cached and now - cached[0] <= self.ttl_seconds:
                return cached[1], True
        if source == "demo":
            snapshot = make_demo_live_snapshot()
        else:
            snapshot = fetch_live_market_snapshot(market)
        snapshot["events"] = detect_market_events(snapshot)
        top = snapshot["events"][0] if snapshot["events"] else None
        friendly = snapshot.get("friendly", {})
        validation = snapshot.get("validation", {})
        snapshot["fast_view"] = {
            "headline": top.get("title") if top else friendly.get("headline", "단기 흐름을 확인 중입니다."),
            "severity": top.get("severity", 0) if top else 0,
            "requires_ai_refresh": bool((top and top.get("severity", 0) >= 4) or validation.get("status") == "warning"),
            "data_warning": validation.get("status") == "warning",
        }
        with self._lock:
            self._cache[key] = (now, snapshot)
        return snapshot, False


class AnalysisService:
    """Runs BitScope V5 with a slow-layer cache and request-scoped LLM budget."""
    def __init__(self) -> None:
        self.ttl_seconds = ANALYSIS_CACHE_TTL_SECONDS
        self._cache: dict[tuple[str, int, str, str, str, str], CacheEntry] = {}
        self._lock = threading.Lock()

    def analyze(self, market: str, history_years: int, source: SourceMode = "live", question: str = "", client_key: str = "anonymous", language: str = "ko", current_exposure_pct: float | None = None):
        language = "en" if language == "en" else "ko"
        normalized_question = " ".join((question or "").split()).strip().lower()
        exposure_key = "none" if current_exposure_pct is None else f"{float(current_exposure_pct):.1f}"
        key = (market, history_years, source, normalized_question, language, exposure_key)
        now = time.monotonic()
        if source == "live":
            with self._lock:
                cached = self._cache.get(key)
                if cached and now - cached.created_at <= self.ttl_seconds:
                    cached_usage = dict(cached.llm_usage)
                    cached_usage.update({"mode": "cache", "reason": "cache_hit_no_new_llm_cost", "calls_used": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
                    return cached.state, True, cached_usage

        reservation = usage_guard.reserve_llm_analysis(client_key, llm_configured=llm_configured())
        orchestrator = BTCAgentOrchestrator(market=market, history_years=history_years)
        with llm_budget_context(allowed=reservation.allowed, reason=reservation.reason) as budget:
            if source == "demo":
                market_df = make_demo_market_data(days=max(450, history_years * 365))
                state = orchestrator.run(market_df=market_df, question=question, source=source, language=language, current_exposure_pct=current_exposure_pct)
            else:
                state = orchestrator.run(question=question, source=source, language=language, current_exposure_pct=current_exposure_pct)

        budget_snapshot = budget.snapshot()
        if reservation.reserved and budget_snapshot["calls_used"] == 0:
            usage_guard.release_llm_reservation(client_key, reservation)
        quota = usage_guard.status(client_key)
        llm_usage = {**budget_snapshot, "mode": "llm" if budget_snapshot["calls_used"] > 0 else "fallback", "reason": budget_snapshot.get("reason") or reservation.reason, "quota": quota}
        if source == "live":
            with self._lock:
                self._cache[key] = CacheEntry(now, state, llm_usage)
        return state, False, llm_usage


analysis_service = AnalysisService()
live_snapshot_service = LiveSnapshotService()
