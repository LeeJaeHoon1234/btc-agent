from __future__ import annotations

from src.agents.v5.council_agent import build_agent_council
from src.core.orchestrator import BTCAgentOrchestrator
from src.core.v5.fact_registry import split_facts_and_priors
from src.engines.v5.portfolio_engine import build_portfolio_plan
from src.engines.v5.risk_governor import apply_risk_governor
from src.tools.demo_data import make_demo_market_data


def test_v5_raw_facts_do_not_leak_direction_or_strength():
    signals = [{"id": "x", "domain": "price", "horizons": ["NOW"], "fact": "price moved", "simple": "move", "value": 1.2, "freshness": "live", "direction": 1, "strength": 0.9}]
    facts, priors = split_facts_and_priors(signals)
    assert "direction" not in facts[0]
    assert "strength" not in facts[0]
    assert priors["x"]["direction"] == 1
    assert priors["x"]["source"] == "deterministic_fallback_only"


def test_specialist_stance_beats_deterministic_prior_when_available():
    facts = [{"id": "d1", "domain": "derivatives", "horizons": ["1W"], "fact": "funding", "simple": "funding", "value": 0.1, "freshness": "live"}]
    priors = {"d1": {"direction": 1, "strength": 1.0}}
    council = build_agent_council(
        facts=facts,
        priors=priors,
        forecasts={"1W": {"q10_return_pct": -4}},
        market_state={"acute_state": "normal"},
        data_health={"price": {"status": "ok"}, "intraday": {"status": "ok"}},
        events=[],
        specialist_views={"derivatives": {"regime": "BEARISH_LEVERAGE", "score": -30, "confidence": 0.8, "summary": "bearish leverage"}},
    )
    assert council["agents"]["derivatives"]["stance"] == "BEARISH"
    assert council["agents"]["derivatives"]["source"] == "independent_specialist"


def test_risk_governor_is_direction_aware_and_never_increases_exposure():
    base = dict(
        proposed_exposure_pct=80,
        forecasts={"1W": {"q10_return_pct": -4}, "1M": {"q10_return_pct": -8}},
        data_health={"price": {"status": "ok"}, "intraday": {"status": "ok"}},
        council={"disagreement": 0.1},
    )
    up = apply_risk_governor(**base, market_state={"acute_state": "volatility_shock_up"}, events=[{"severity": 5, "direction": 1, "kind": "shock"}])
    down = apply_risk_governor(**base, market_state={"acute_state": "volatility_shock_down"}, events=[{"severity": 5, "direction": -1, "kind": "shock"}])
    assert up["approved_exposure_pct"] == 80
    assert down["approved_exposure_pct"] <= 20
    assert down["approved_exposure_pct"] <= down["proposed_exposure_pct"]


def test_portfolio_engine_obeys_single_change_limit():
    result = build_portfolio_plan(
        current_price=100_000_000,
        current_exposure_pct=10,
        risk_governor={"approved_exposure_pct": 80, "max_single_change_pct": 20},
        forecasts={"NOW": {"dispersion_pct": 1}, "1W": {"q25_return_pct": -4, "q10_return_pct": -10}, "1M": {"q75_return_pct": 8, "q90_return_pct": 15}},
        meta_decision={"action": "INCREASE"},
    )
    assert result["target_exposure_pct"] == 80
    assert result["recommended_change_pct"] == 20
    assert result["next_exposure_pct"] == 30


def test_v5_demo_pipeline_has_calibrated_distributions_and_governed_portfolio():
    state = BTCAgentOrchestrator(history_years=3).run(
        market_df=make_demo_market_data(days=900, seed=7),
        source="demo",
        language="ko",
        current_exposure_pct=40,
    )
    assert set(state.forecasts) == {"NOW", "TODAY", "1W", "1M", "1Y"}
    for horizon, forecast in state.forecasts.items():
        if not forecast.get("available"):
            continue
        assert forecast["q10_return_pct"] <= forecast["median_return_pct"] <= forecast["q90_return_pct"]
        assert 0 <= forecast["probability_up_pct"] <= 100
        assert 0.25 <= forecast["confidence"] <= 0.76
    assert state.forecasts["1Y"]["confidence"] <= 0.55
    assert state.forecasts["1Y"]["probability_up_pct"] > 0 or state.forecasts["1Y"].get("raw_probability_up_pct", 1) > 0
    assert state.risk_governor["approved_exposure_pct"] <= state.risk_governor["proposed_exposure_pct"]
    assert 0 <= state.portfolio["next_exposure_pct"] <= 100
    assert abs(state.portfolio["recommended_change_pct"]) <= state.risk_governor["max_single_change_pct"]
    assert all("direction" not in fact and "strength" not in fact for fact in state.facts)


def test_walkforward_validator_truncates_and_returns_bounded_metrics():
    from src.validation.v5_walkforward import validate_forecasts_walkforward
    result = validate_forecasts_walkforward(make_demo_market_data(days=1000, seed=11), horizons=("1W", "1M"), max_points_per_horizon=4)
    assert result["validation"] == "strict_walkforward_forecast_layer"
    for metrics in result["by_horizon"].values():
        if metrics["samples"] == 0:
            continue
        assert 0 <= metrics["direction_accuracy"] <= 1
        assert 0 <= metrics["mean_brier"] <= 1
        assert 0 <= metrics["q10_q90_coverage"] <= 1
