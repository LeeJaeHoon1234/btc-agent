from __future__ import annotations

import hashlib
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator

from config.settings import (
    COST_GUARD_ENABLED,
    GLOBAL_DAILY_LLM_ANALYSIS_LIMIT,
    IP_DAILY_LLM_ANALYSIS_LIMIT,
    IP_DAILY_REQUEST_LIMIT,
    IP_HOURLY_REQUEST_LIMIT,
    MAX_LLM_CALLS_PER_ANALYSIS,
    MAX_LLM_TOKENS_PER_ANALYSIS,
)


class LLMBudgetExceeded(RuntimeError):
    """Raised when a request has exhausted its request-scoped LLM budget."""


@dataclass
class LLMBudget:
    allowed: bool
    reason: str
    max_calls: int
    max_tokens: int
    calls_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def can_call(self) -> bool:
        with self._lock:
            if not self.allowed:
                return False
            if self.max_calls >= 0 and self.calls_used >= self.max_calls:
                return False
            if self.max_tokens > 0 and self.total_tokens >= self.max_tokens:
                return False
            return True

    def authorize_call(self) -> None:
        with self._lock:
            if not self.allowed:
                raise LLMBudgetExceeded(self.reason or "LLM disabled for this request")
            if self.max_calls >= 0 and self.calls_used >= self.max_calls:
                self.reason = "per_analysis_call_limit"
                raise LLMBudgetExceeded("Per-analysis LLM call limit reached")
            if self.max_tokens > 0 and self.total_tokens >= self.max_tokens:
                self.reason = "per_analysis_token_limit"
                raise LLMBudgetExceeded("Per-analysis LLM token budget reached")
            self.calls_used += 1

    def record_tokens(self, input_tokens: int = 0, output_tokens: int = 0, total_tokens: int = 0) -> None:
        with self._lock:
            self.input_tokens += max(0, int(input_tokens or 0))
            self.output_tokens += max(0, int(output_tokens or 0))
            if total_tokens:
                self.total_tokens += max(0, int(total_tokens))
            else:
                self.total_tokens += max(0, int(input_tokens or 0)) + max(0, int(output_tokens or 0))

    def snapshot(self) -> dict:
        with self._lock:
            exhausted = (
                (self.max_calls >= 0 and self.calls_used >= self.max_calls)
                or (self.max_tokens > 0 and self.total_tokens >= self.max_tokens)
            )
            reason = self.reason
            if exhausted and reason in {"", "allowed"}:
                if self.max_calls >= 0 and self.calls_used >= self.max_calls:
                    reason = "per_analysis_call_limit"
                elif self.max_tokens > 0 and self.total_tokens >= self.max_tokens:
                    reason = "per_analysis_token_limit"
            return {
                "allowed": self.allowed,
                "reason": reason,
                "calls_used": self.calls_used,
                "max_calls": self.max_calls,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
                "max_tokens": self.max_tokens,
                "budget_exhausted": exhausted,
            }


_current_budget: ContextVar[LLMBudget | None] = ContextVar("btc_agent_llm_budget", default=None)


def current_llm_budget() -> LLMBudget | None:
    return _current_budget.get()


def request_llm_enabled() -> bool:
    budget = current_llm_budget()
    return True if budget is None else budget.can_call()


@contextmanager
def llm_budget_context(*, allowed: bool, reason: str) -> Iterator[LLMBudget]:
    budget = LLMBudget(
        allowed=allowed,
        reason=reason,
        max_calls=max(0, MAX_LLM_CALLS_PER_ANALYSIS),
        max_tokens=max(0, MAX_LLM_TOKENS_PER_ANALYSIS),
    )
    token = _current_budget.set(budget)
    try:
        yield budget
    finally:
        _current_budget.reset(token)


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    reason: str
    retry_after_seconds: int | None = None


@dataclass(frozen=True)
class LLMReservation:
    allowed: bool
    reason: str
    reserved: bool


class UsageGuard:
    """Process-local abuse/cost guard for a single Render worker.

    The hard provider-side monthly spend cap still belongs in the OpenAI dashboard.
    These counters intentionally keep no raw IP address: callers are represented by a
    short SHA-256 hash and counters are reset naturally with process restarts.
    """

    def __init__(
        self,
        *,
        enabled: bool = COST_GUARD_ENABLED,
        ip_hourly_request_limit: int = IP_HOURLY_REQUEST_LIMIT,
        ip_daily_request_limit: int = IP_DAILY_REQUEST_LIMIT,
        ip_daily_llm_limit: int = IP_DAILY_LLM_ANALYSIS_LIMIT,
        global_daily_llm_limit: int = GLOBAL_DAILY_LLM_ANALYSIS_LIMIT,
    ) -> None:
        self.enabled = enabled
        self.ip_hourly_request_limit = max(0, ip_hourly_request_limit)
        self.ip_daily_request_limit = max(0, ip_daily_request_limit)
        self.ip_daily_llm_limit = max(0, ip_daily_llm_limit)
        self.global_daily_llm_limit = max(0, global_daily_llm_limit)
        self._request_hourly: dict[tuple[str, str], int] = {}
        self._request_daily: dict[tuple[str, str], int] = {}
        self._llm_daily: dict[tuple[str, str], int] = {}
        self._global_llm_daily: dict[str, int] = {}
        self._lock = threading.Lock()

    @staticmethod
    def anonymize_client(raw_client: str | None) -> str:
        value = (raw_client or "unknown").strip() or "unknown"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _keys(now: datetime | None = None) -> tuple[str, str]:
        current = now or datetime.now(timezone.utc)
        return current.strftime("%Y-%m-%d"), current.strftime("%Y-%m-%dT%H")

    @staticmethod
    def _seconds_until_next_hour(now: datetime | None = None) -> int:
        current = now or datetime.now(timezone.utc)
        next_hour = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return max(1, int((next_hour - current).total_seconds()))

    @staticmethod
    def _seconds_until_next_day(now: datetime | None = None) -> int:
        current = now or datetime.now(timezone.utc)
        next_day = current.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return max(1, int((next_day - current).total_seconds()))

    def _cleanup_locked(self, day_key: str, hour_key: str) -> None:
        self._request_hourly = {k: v for k, v in self._request_hourly.items() if k[1] == hour_key}
        self._request_daily = {k: v for k, v in self._request_daily.items() if k[1] == day_key}
        self._llm_daily = {k: v for k, v in self._llm_daily.items() if k[1] == day_key}
        self._global_llm_daily = {k: v for k, v in self._global_llm_daily.items() if k == day_key}

    def register_request(self, client_key: str, now: datetime | None = None) -> RateDecision:
        if not self.enabled:
            return RateDecision(True, "guard_disabled")

        day_key, hour_key = self._keys(now)
        with self._lock:
            self._cleanup_locked(day_key, hour_key)
            hourly_key = (client_key, hour_key)
            daily_key = (client_key, day_key)
            hourly_used = self._request_hourly.get(hourly_key, 0)
            daily_used = self._request_daily.get(daily_key, 0)

            if self.ip_hourly_request_limit and hourly_used >= self.ip_hourly_request_limit:
                return RateDecision(False, "ip_hourly_request_limit", self._seconds_until_next_hour(now))
            if self.ip_daily_request_limit and daily_used >= self.ip_daily_request_limit:
                return RateDecision(False, "ip_daily_request_limit", self._seconds_until_next_day(now))

            self._request_hourly[hourly_key] = hourly_used + 1
            self._request_daily[daily_key] = daily_used + 1
            return RateDecision(True, "allowed")

    def reserve_llm_analysis(self, client_key: str, *, llm_configured: bool, now: datetime | None = None) -> LLMReservation:
        if not llm_configured:
            return LLMReservation(False, "llm_not_configured", False)
        if not self.enabled:
            return LLMReservation(True, "guard_disabled", False)

        day_key, hour_key = self._keys(now)
        with self._lock:
            self._cleanup_locked(day_key, hour_key)
            client_daily_key = (client_key, day_key)
            client_used = self._llm_daily.get(client_daily_key, 0)
            global_used = self._global_llm_daily.get(day_key, 0)

            if self.ip_daily_llm_limit and client_used >= self.ip_daily_llm_limit:
                return LLMReservation(False, "ip_daily_llm_limit", False)
            if self.global_daily_llm_limit and global_used >= self.global_daily_llm_limit:
                return LLMReservation(False, "global_daily_llm_limit", False)

            self._llm_daily[client_daily_key] = client_used + 1
            self._global_llm_daily[day_key] = global_used + 1
            return LLMReservation(True, "allowed", True)

    def release_llm_reservation(self, client_key: str, reservation: LLMReservation, now: datetime | None = None) -> None:
        if not reservation.reserved or not self.enabled:
            return
        day_key, _ = self._keys(now)
        with self._lock:
            client_key_day = (client_key, day_key)
            if self._llm_daily.get(client_key_day, 0) > 0:
                self._llm_daily[client_key_day] -= 1
            if self._global_llm_daily.get(day_key, 0) > 0:
                self._global_llm_daily[day_key] -= 1

    def status(self, client_key: str, now: datetime | None = None) -> dict:
        day_key, hour_key = self._keys(now)
        with self._lock:
            self._cleanup_locked(day_key, hour_key)
            hourly_used = self._request_hourly.get((client_key, hour_key), 0)
            daily_used = self._request_daily.get((client_key, day_key), 0)
            ip_llm_used = self._llm_daily.get((client_key, day_key), 0)
            global_llm_used = self._global_llm_daily.get(day_key, 0)

        return {
            "enabled": self.enabled,
            "scope": "process_memory",
            "request": {
                "hourly_used": hourly_used,
                "hourly_limit": self.ip_hourly_request_limit,
                "daily_used": daily_used,
                "daily_limit": self.ip_daily_request_limit,
            },
            "llm": {
                "ip_daily_used": ip_llm_used,
                "ip_daily_limit": self.ip_daily_llm_limit,
                "global_daily_used": global_llm_used,
                "global_daily_limit": self.global_daily_llm_limit,
                "reset_at_utc": (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat(),
            },
        }

    def reset_for_tests(self) -> None:
        with self._lock:
            self._request_hourly.clear()
            self._request_daily.clear()
            self._llm_daily.clear()
            self._global_llm_daily.clear()


usage_guard = UsageGuard()
