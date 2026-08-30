from datetime import datetime, timezone

import pytest

from src.core.v3.usage_guard import LLMBudgetExceeded, UsageGuard, llm_budget_context


def test_request_rate_limit_blocks_after_hourly_limit():
    guard = UsageGuard(
        enabled=True,
        ip_hourly_request_limit=2,
        ip_daily_request_limit=10,
        ip_daily_llm_limit=3,
        global_daily_llm_limit=30,
    )
    client = guard.anonymize_client("203.0.113.9")
    now = datetime(2026, 8, 30, 8, 0, tzinfo=timezone.utc)

    assert guard.register_request(client, now).allowed is True
    assert guard.register_request(client, now).allowed is True
    blocked = guard.register_request(client, now)
    assert blocked.allowed is False
    assert blocked.reason == "ip_hourly_request_limit"


def test_llm_quota_falls_back_without_blocking_analysis():
    guard = UsageGuard(
        enabled=True,
        ip_hourly_request_limit=10,
        ip_daily_request_limit=10,
        ip_daily_llm_limit=1,
        global_daily_llm_limit=10,
    )
    client = guard.anonymize_client("203.0.113.10")
    now = datetime(2026, 8, 30, 8, 0, tzinfo=timezone.utc)

    first = guard.reserve_llm_analysis(client, llm_configured=True, now=now)
    second = guard.reserve_llm_analysis(client, llm_configured=True, now=now)
    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "ip_daily_llm_limit"


def test_global_llm_quota_applies_across_clients():
    guard = UsageGuard(
        enabled=True,
        ip_hourly_request_limit=10,
        ip_daily_request_limit=10,
        ip_daily_llm_limit=10,
        global_daily_llm_limit=1,
    )
    now = datetime(2026, 8, 30, 8, 0, tzinfo=timezone.utc)
    a = guard.anonymize_client("203.0.113.11")
    b = guard.anonymize_client("203.0.113.12")

    assert guard.reserve_llm_analysis(a, llm_configured=True, now=now).allowed is True
    blocked = guard.reserve_llm_analysis(b, llm_configured=True, now=now)
    assert blocked.allowed is False
    assert blocked.reason == "global_daily_llm_limit"


def test_per_analysis_budget_caps_llm_calls():
    with llm_budget_context(allowed=True, reason="allowed") as budget:
        # The configured limit can be larger than 2, so force a small cap for this unit test.
        budget.max_calls = 2
        budget.authorize_call()
        budget.authorize_call()
        with pytest.raises(LLMBudgetExceeded):
            budget.authorize_call()
        snap = budget.snapshot()
        assert snap["calls_used"] == 2
        assert snap["budget_exhausted"] is True
