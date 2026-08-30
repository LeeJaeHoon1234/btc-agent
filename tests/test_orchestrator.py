import os

os.environ["USE_LLM"] = "false"

from src.core.orchestrator import BTCAgentOrchestrator
from src.tools.demo_data import make_demo_market_data


def test_full_agent_pipeline_runs_without_network():
    df = make_demo_market_data(days=900, seed=7)
    state = BTCAgentOrchestrator(history_years=3).run(market_df=df)

    assert state.final_decision is not None
    assert state.final_decision.action in {"매수", "관망", "비중축소"}
    assert 0 <= state.entry["score"] <= 100
    assert 0 <= state.exit["score"] <= 100
    assert state.gate.route in {"fast_path", "deep_analysis"}
    assert state.explanation.get("headline")

    expected = {
        "indicators",
        "technical_agent",
        "ml_predictor",
        "regime_tool",
        "similarity_tool",
        "cycle_tool",
        "entry_engine",
        "exit_engine",
        "confidence_gate",
        "risk_agent",
        "decision_agent",
        "position_engine",
        "explanation_agent",
    }
    assert expected.issubset(set(state.logs))
