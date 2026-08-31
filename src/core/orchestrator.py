from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from config.settings import HISTORY_YEARS, MARKET, SIMILARITY_EXCLUDE_RECENT_DAYS, SIMILARITY_TOP_K
from src.agents.cycle_agent import run_cycle_agent
from src.agents.risk_agent import run_risk_agent
from src.agents.technical_agent import run_technical_agent
from src.agents.v3.planner_agent import DEFAULT_QUESTION
from src.agents.v3.research_orchestrator import collect_evidence, run_research
from src.agents.v4.autonomy_agent import analyze_horizons
from src.agents.v4.critic_agent import critique_horizons
from src.agents.v4.user_writer import write_user_view
from src.core.schemas import Decision
from src.core.state import AgentState
from src.engines.confidence_gate import evaluate_confidence_gate
from src.engines.entry_engine import score_entry
from src.engines.exit_engine import score_exit
from src.engines.position_engine import apply_position_plan
from src.engines.research_engine import apply_research_adjustment
from src.engines.v4.horizon_engine import build_horizon_fallbacks, build_signal_registry
from src.tools.cycle_tool import analyze_cycle
from src.tools.demo_data import make_demo_market_data
from src.tools.event_detector import detect_market_events
from src.tools.indicators import add_indicators
from src.tools.live_market import fetch_live_market_snapshot, make_demo_live_snapshot
from src.tools.market_data import get_daily_candles_history
from src.tools.ml_predictor import predict_latest
from src.tools.regime_tool import detect_regime
from src.tools.research.derivatives_tool import fetch_btc_derivatives
from src.tools.research.flow_tool import fetch_etf_flow
from src.tools.research.macro_tool import fetch_macro_snapshot
from src.tools.research.news_search_tool import search_btc_news
from src.tools.research.onchain_tool import fetch_network_snapshot
from src.tools.research.sentiment_tool import fetch_fear_greed
from src.tools.similarity_tool import find_similar_periods


class BTCAgentOrchestrator:
    """BTC Agent V4: deterministic facts + autonomous multi-horizon interpretation."""

    def __init__(self, market: str = MARKET, history_years: int = HISTORY_YEARS):
        self.market = market
        self.history_years = history_years

    @staticmethod
    def _health_item(available: bool, fetched_at=None, provider=None, cadence=None, errors=None) -> dict:
        return {
            "status": "ok" if available else "unavailable",
            "fetched_at": fetched_at,
            "provider": provider,
            "cadence": cadence,
            "errors": (errors or [])[:3],
        }

    def _external_inputs(self, source: str, daily_df) -> tuple[dict, dict]:
        if source == "demo":
            live = make_demo_live_snapshot(daily_df)
            now = datetime.now(timezone.utc).isoformat()
            raw = {
                "derivatives": {"available": True, "provider": "demo", "funding_rate": 0.00012, "open_interest": 81234.0, "open_interest_change_24h_pct": -2.7, "global_long_short_ratio": 1.25, "top_trader_position_ratio": 1.42, "taker_buy_sell_ratio": 1.08, "basis_rate": 0.0004, "fetched_at": now},
                "macro": {"available": True, "provider": "demo", "dollar_index": 99.2, "dollar_change_window_pct": -0.6, "us10y_yield": 3.91, "us10y_change_window_pct": -1.4, "fetched_at": now},
                "news": {"available": True, "provider": "demo", "documents": [{"title": "Bitcoin rebounds after intraday flush as spot demand returns", "url": "https://example.com/demo-1", "source": "Demo News", "published_at": now, "text": "Bitcoin rebounds after intraday flush as spot demand returns"}], "errors": [], "fetched_at": now},
                "flow": {"available": True, "provider": "demo", "latest_total_musd": 310.0, "five_session_total_musd": 760.0, "latest_date_label": "demo", "fetched_at": now, "errors": []},
                "sentiment": {"available": True, "provider": "demo", "value": 68, "classification": "Greed", "change_7obs": 5, "fetched_at": now, "errors": []},
                "onchain": {"available": True, "provider": "demo", "fee_fastest_sat_vb": 8, "hash_rate": 1.0, "valuation_metrics_available": False, "missing_valuation_metrics": ["MVRV", "SOPR"], "fetched_at": now, "errors": []},
            }
            return live, raw

        jobs = {}
        results = {}
        with ThreadPoolExecutor(max_workers=7) as pool:
            for name, fn in {
                "live": lambda: fetch_live_market_snapshot(self.market),
                "derivatives": fetch_btc_derivatives,
                "macro": fetch_macro_snapshot,
                "news": search_btc_news,
                "flow": fetch_etf_flow,
                "sentiment": fetch_fear_greed,
                "onchain": fetch_network_snapshot,
            }.items():
                jobs[pool.submit(fn)] = name
            for future in as_completed(jobs):
                name = jobs[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    results[name] = {"available": False, "provider": name, "errors": [f"{type(exc).__name__}: {exc}"], "fetched_at": datetime.now(timezone.utc).isoformat()}
        return results.pop("live", {"available": False, "errors": ["live snapshot missing"]}), results

    def run(self, market_df=None, question: str | None = None, source: str = "live") -> AgentState:
        state = AgentState()
        state.question = (question or DEFAULT_QUESTION).strip()
        injected = market_df is not None

        # Slow layer: daily context + existing model/cycle assets.
        state.add_log("daily_market_data")
        if market_df is None:
            market_df = get_daily_candles_history(market=self.market, years=self.history_years)
        state.add_log("daily_indicators")
        df = add_indicators(market_df)
        state.market_df = df
        latest_row = df.dropna().iloc[-1]
        latest_keys = [
            "date", "close", "rsi14", "ma20_gap_pct", "ma20_slope_5d", "ma50_gap_pct", "ma50_slope_10d",
            "ma200_gap_pct", "ma200_slope_20d", "ma350_gap_pct", "volume_ratio", "volume_zscore_30d",
            "return_1d", "return_3d", "return_7d", "return_14d", "return_30d", "return_90d", "return_180d", "return_365d",
            "drawdown_from_ath_pct", "drawdown_30d_pct", "drawdown_90d_pct", "drawdown_365d_pct",
            "volatility_7d_pct", "volatility_30d_pct", "volatility_90d_pct", "macd", "macd_signal", "macd_hist",
            "bb_width_pct", "bb_position", "atr14_pct", "adx14", "plus_di14", "minus_di14", "stoch_k", "stoch_d", "roc14", "obv_slope_10d"
        ]
        state.latest = {}
        for key in latest_keys:
            if key not in latest_row.index:
                continue
            value = latest_row[key]
            if key == "date":
                state.latest[key] = str(value)
            else:
                try:
                    value = float(value)
                    if value == value and value not in {float("inf"), float("-inf")}:
                        state.latest[key] = value
                except (TypeError, ValueError):
                    pass

        state.add_log("technical_core")
        state.technical = run_technical_agent(df)
        state.add_log("ml_30d_support")
        state.ml = predict_latest(df)
        state.add_log("regime_core")
        state.regime = detect_regime(df)
        state.add_log("historical_similarity")
        state.similarity = find_similar_periods(df, top_k=SIMILARITY_TOP_K, exclude_recent_days=SIMILARITY_EXCLUDE_RECENT_DAYS)
        state.add_log("cycle_core")
        state.cycle = analyze_cycle(df)
        state.cycle["agent_view"] = run_cycle_agent(state.cycle)
        state.entry = score_entry(state.technical, state.ml, state.regime, state.similarity)
        state.exit = score_exit(state.latest, state.cycle)
        state.gate = evaluate_confidence_gate(state.technical, state.ml, state.regime, state.similarity, state.entry, state.exit)

        # Fast/external layer: all fetches are best-effort and independently health-tracked.
        state.add_log("v4_live_and_external_data")
        fetch_source = "demo" if source == "demo" or injected else "live"
        state.live, raw = self._external_inputs(fetch_source, df)
        state.external = {k: v for k, v in raw.items() if k in {"flow", "sentiment", "onchain"}}
        ticker_price = (state.live.get("ticker") or {}).get("price")
        if ticker_price is not None:
            state.latest["live_price"] = float(ticker_price)
            state.latest["live_fetched_at"] = state.live.get("fetched_at")

        state.data_health = {
            "price": self._health_item(bool(state.live.get("available")), state.live.get("fetched_at"), state.live.get("provider"), "tick in browser / ~10s REST snapshot", state.live.get("errors")),
            "intraday": self._health_item(bool(state.live.get("metrics")), state.live.get("fetched_at"), "Upbit 5m candles + trades + orderbook", "~10s snapshot", state.live.get("errors")),
            "derivatives": self._health_item(bool(raw.get("derivatives", {}).get("available")), raw.get("derivatives", {}).get("fetched_at"), raw.get("derivatives", {}).get("provider"), "minutes", raw.get("derivatives", {}).get("errors")),
            "macro": self._health_item(bool(raw.get("macro", {}).get("available")), raw.get("macro", {}).get("fetched_at"), raw.get("macro", {}).get("provider"), "hours/daily", raw.get("macro", {}).get("errors")),
            "news": self._health_item(bool(raw.get("news", {}).get("available")), raw.get("news", {}).get("fetched_at"), raw.get("news", {}).get("provider"), "minutes", raw.get("news", {}).get("errors")),
            "etf_flow": self._health_item(bool(raw.get("flow", {}).get("available")), raw.get("flow", {}).get("fetched_at"), raw.get("flow", {}).get("provider"), "daily", raw.get("flow", {}).get("errors")),
            "sentiment": self._health_item(bool(raw.get("sentiment", {}).get("available")), raw.get("sentiment", {}).get("fetched_at"), raw.get("sentiment", {}).get("provider"), "daily", raw.get("sentiment", {}).get("errors")),
            "onchain_network": self._health_item(bool(raw.get("onchain", {}).get("available")), raw.get("onchain", {}).get("fetched_at"), raw.get("onchain", {}).get("provider"), "minutes/hours", raw.get("onchain", {}).get("errors")),
            "ml_30d": self._health_item(bool(state.ml.get("available")), state.latest.get("date"), "saved LightGBM", "daily", []),
        }

        # Keep V3 specialist research in Advanced, but routing itself is deterministic in V4 to save a call.
        state.plan = {"objective": state.question, "selected_skills": ["technical", "derivatives", "macro", "news", "historical", "risk"], "reason": "V4 default analysis always inspects broad cross-domain evidence.", "source": "v4_deterministic"}
        state.add_log("specialist_research")
        state.experts, state.research = run_research(state.question, state.plan, state, source=fetch_source, raw_inputs=raw)
        state.evidence = collect_evidence(state.experts)
        state.research_adjustment = apply_research_adjustment(state.entry, state.exit, state.research)
        state.risk = run_risk_agent(state)

        deriv_raw = ((state.experts.get("derivatives") or {}).get("raw") or raw.get("derivatives", {}))
        state.events = detect_market_events(state.live, deriv_raw)
        state.add_log("event_detector")

        # V4 autonomy: facts -> candidate signals -> horizon-aware LLM -> independent critic -> plain writer.
        state.signals = build_signal_registry(state)
        fallbacks = build_horizon_fallbacks(state.signals, state.events)
        state.add_log("horizon_analyst")
        state.autonomy = analyze_horizons(state.signals, state.events, fallbacks, state.data_health, state.research)
        state.horizons = state.autonomy.get("horizons", fallbacks)
        state.add_log("v4_critic")
        state.v4_critic = critique_horizons(state.autonomy, state.signals, state.events, state.data_health)
        state.add_log("plain_language_writer")
        state.user_view = write_user_view(state.autonomy, state.signals, state.events, state.v4_critic)

        # Backward-compatible V2-style final_decision for API consumers, derived from V4 actions.
        action_map = {"분할매수 검토": "매수", "피하기": "관망", "기다림": "관망"}
        add_action = state.user_view.get("actions", {}).get("add", "기다림")
        hold_action = state.user_view.get("actions", {}).get("hold", "유지")
        final_action = "비중축소" if "줄이기" in hold_action else action_map.get(add_action, "관망")
        now_conf = float(state.horizons.get("NOW", {}).get("confidence", 0.55))
        state.final_decision = Decision(final_action, now_conf, state.user_view.get("headline", "V4 horizon decision"), state.user_view.get("why", []), state.user_view.get("watch", []), source="v4")
        state.draft_decision = state.final_decision
        state.final_decision = apply_position_plan(state.final_decision, float(state.entry.get("score", 50)), float(state.exit.get("score", 0)))
        state.explanation = {
            "headline": state.user_view.get("headline"), "summary": state.user_view.get("summary"),
            "positives": state.user_view.get("why", []), "cautions": state.horizons.get("NOW", {}).get("risks", []),
            "strategy": [f"기존 보유: {state.user_view.get('actions', {}).get('hold')}", f"추가 매수: {state.user_view.get('actions', {}).get('add')}", f"익절: {state.user_view.get('actions', {}).get('take_profit')}"],
            "recheck": state.user_view.get("watch", []), "source": state.user_view.get("source", "fallback"),
        }
        return state
