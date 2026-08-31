import os
os.environ["USE_LLM"] = "false"

from src.core.orchestrator import BTCAgentOrchestrator
from src.tools.demo_data import make_demo_market_data


def test_full_v4_pipeline_runs_without_network():
    state = BTCAgentOrchestrator(history_years=3).run(market_df=make_demo_market_data(days=900, seed=7), source="demo")
    assert state.final_decision is not None
    assert state.final_decision.action in {"매수", "관망", "비중축소"}
    assert 0 <= state.entry["score"] <= 100 and 0 <= state.exit["score"] <= 100
    assert set(state.horizons) == {"NOW", "TODAY", "1W", "1M", "1Y"}
    assert state.live["available"] is True
    assert state.events
    assert len(state.signals) >= 20
    assert state.user_view["headline"]
    assert {"hold", "add", "take_profit"}.issubset(state.user_view["actions"])
    expected = {"daily_indicators", "technical_core", "ml_30d_support", "v4_live_and_external_data", "specialist_research", "event_detector", "horizon_analyst", "v4_critic", "plain_language_writer"}
    assert expected.issubset(set(state.logs))
