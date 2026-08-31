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



def test_explicit_technical_neutral_stance_is_not_overridden_by_score():
    council = build_agent_council(
        facts=[{"id": "t1", "domain": "technical", "horizons": ["NOW"], "fact": "technical", "simple": "기술", "value": 1, "freshness": "live"}],
        priors={"t1": {"direction": 1, "strength": 1.0}},
        forecasts={"1W": {"q10_return_pct": -4}},
        market_state={"acute_state": "normal"},
        data_health={"price": {"status": "ok"}}, events=[],
        specialist_views={"technical": {"stance": "NEUTRAL", "raw_score": 63, "score": 26, "confidence": 0.75, "summary": "Technical stance is neutral."}},
        language="ko",
    )
    assert council["agents"]["technical"]["stance"] == "NEUTRAL"
    assert "63/100" in council["agents"]["technical"]["thesis"]


def test_etf_parser_reads_final_total_cell_and_parenthesis_as_negative():
    from src.tools.research.flow_tool import _parse_rows
    html = """<table><tr><td>27 Aug 2026</td><td>277.6</td><td>(83.6)</td><td>242.3</td></tr>
    <tr><td>28 Aug 2026</td><td>(33.4)</td><td>0.0</td><td>(201.9)</td></tr></table>"""
    rows = _parse_rows(html)
    assert rows[-1]["date_label"] == "28 Aug 2026"
    assert rows[-1]["total_musd"] == -201.9

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


def test_orchestrator_preserves_specialist_stance_and_raw_score_end_to_end_boundary():
    views = BTCAgentOrchestrator._independent_specialist_views({
        "technical": {
            "available": True,
            "stance": "NEUTRAL",
            "raw_score": 63,
            "score": 26,
            "confidence": 0.75,
            "summary": "Technical stance is neutral.",
            "evidence": ["가격이 MA200 위", "MA20 단기 추세 하락"],
        }
    })
    assert views["technical"]["stance"] == "NEUTRAL"
    assert views["technical"]["raw_score"] == 63
    council = build_agent_council(
        facts=[{"id": "t1", "domain": "technical", "horizons": ["NOW"], "fact": "technical", "simple": "기술", "value": 1, "freshness": "live"}],
        priors={"t1": {"direction": 1, "strength": 1.0}}, forecasts={"1W": {"q10_return_pct": -4}},
        market_state={"acute_state": "normal"}, data_health={"price": {"status": "ok"}}, events=[],
        specialist_views=views, language="ko",
    )
    assert council["agents"]["technical"]["stance"] == "NEUTRAL"
    assert "63/100" in council["agents"]["technical"]["thesis"]
    assert "MA200" in council["agents"]["technical"]["thesis"]


def test_etf_current_new_york_session_is_provisional_not_completed():
    from datetime import datetime, timezone
    from src.tools.research.flow_tool import _completed_rows, _parse_rows
    html = """<table>
      <tr><td>28 Aug 2026</td><td>(33.4)</td><td>(201.9)</td></tr>
      <tr><td>31 Aug 2026</td><td>0.0</td><td>0.0</td></tr>
    </table>"""
    rows = _parse_rows(html)
    completed, provisional = _completed_rows(rows, now=datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc))
    assert [r["date_label"] for r in completed] == ["28 Aug 2026"]
    assert [r["date_label"] for r in provisional] == ["31 Aug 2026"]
    assert completed[-1]["total_musd"] == -201.9


def test_macro_and_news_are_independent_council_members():
    council = build_agent_council(
        facts=[
            {"id": "m1", "domain": "macro", "horizons": ["1W"], "fact": "dxy", "simple": "달러 상승", "value": 1, "freshness": "daily"},
            {"id": "n1", "domain": "news", "horizons": ["1W"], "fact": "headline", "simple": "ETF headline", "value": "x", "freshness": "recent"},
        ],
        priors={"m1": {"direction": -1, "strength": 0.8}, "n1": {"direction": 0, "strength": 0.4}},
        forecasts={"1W": {"q10_return_pct": -4}}, market_state={"acute_state": "normal"},
        data_health={"macro": {"status": "ok"}, "news": {"status": "ok"}}, events=[],
        specialist_views={
            "macro": {"available": True, "regime": "RISK_OFF_HEADWIND", "score": -30, "confidence": 0.8, "evidence": ["DXY up"]},
            "news": {"available": True, "score": 0, "confidence": 0.5, "evidence": ["ETF headline"]},
        }, language="ko",
    )
    assert "macro" in council["agents"]
    assert "news" in council["agents"]
    assert "macro_news" not in council["agents"]


def test_etf_prior_balances_latest_session_with_five_session_trend():
    # Regression for 28 Aug 2026: latest completed session was -201.9M while
    # the latest five completed sessions still summed to +924.5M. The fallback
    # prior should stay mixed rather than overreact to one session.
    from types import SimpleNamespace
    from src.engines.v4.horizon_engine import build_signal_registry
    state = SimpleNamespace(
        latest={}, live={}, experts={"derivatives": {"raw": {}}, "news": {}},
        external={"flow": {"available": True, "latest_total_musd": -201.9, "five_session_total_musd": 924.5, "latest_date_label": "28 Aug 2026"}, "sentiment": {}, "onchain": {}},
        ml={},
    )
    sig = next(x for x in build_signal_registry(state) if x["id"] == "S_ETF_FLOW")
    assert sig["direction"] == 0
    assert sig["strength"] < 0.12
    assert "+924" in sig["simple"] or "+925" in sig["simple"]
