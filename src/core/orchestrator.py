from config.settings import (
    HISTORY_YEARS,
    MARKET,
    MAX_CRITIC_ITERATIONS,
    SIMILARITY_EXCLUDE_RECENT_DAYS,
    SIMILARITY_TOP_K,
)
from src.agents.critic_agent import review_decision
from src.agents.cycle_agent import run_cycle_agent
from src.agents.decision_agent import make_decision, revise_decision
from src.agents.explanation_agent import explain_for_user
from src.agents.risk_agent import run_risk_agent
from src.agents.technical_agent import run_technical_agent
from src.agents.v3.planner_agent import DEFAULT_QUESTION, make_research_plan
from src.agents.v3.research_orchestrator import collect_evidence, run_research
from src.core.state import AgentState
from src.engines.confidence_gate import evaluate_confidence_gate
from src.engines.entry_engine import score_entry
from src.engines.exit_engine import score_exit
from src.engines.position_engine import apply_position_plan
from src.engines.research_engine import apply_research_adjustment
from src.tools.cycle_tool import analyze_cycle
from src.tools.indicators import add_indicators
from src.tools.market_data import get_daily_candles_history
from src.tools.ml_predictor import predict_latest
from src.tools.regime_tool import detect_regime
from src.tools.similarity_tool import find_similar_periods


class BTCAgentOrchestrator:
    def __init__(
        self,
        market: str = MARKET,
        history_years: int = HISTORY_YEARS,
    ):
        self.market = market
        self.history_years = history_years

    def run(self, market_df=None, question: str | None = None, source: str = "live") -> AgentState:
        state = AgentState()
        injected_market_df = market_df is not None
        state.question = (question or DEFAULT_QUESTION).strip()

        # 1) Core market data
        state.add_log("market_data")
        if market_df is None:
            market_df = get_daily_candles_history(
                market=self.market,
                years=self.history_years,
            )

        # 2) Deterministic feature layer
        state.add_log("indicators")
        df = add_indicators(market_df)
        state.market_df = df

        latest_row = df.dropna().iloc[-1]
        state.latest = {
            "date": str(latest_row["date"]),
            "close": float(latest_row["close"]),
            "rsi14": float(latest_row["rsi14"]),
            "ma20_gap_pct": float(latest_row["ma20_gap_pct"]),
            "ma20_slope_5d": float(latest_row["ma20_slope_5d"]),
            "ma200_gap_pct": float(latest_row["ma200_gap_pct"]),
            "ma200_slope_20d": float(latest_row["ma200_slope_20d"]),
            "ma350_gap_pct": float(latest_row["ma350_gap_pct"]),
            "volume_ratio": float(latest_row["volume_ratio"]),
            "return_3d": float(latest_row["return_3d"]),
            "return_7d": float(latest_row["return_7d"]),
            "return_30d": float(latest_row["return_30d"]),
            "return_90d": float(latest_row["return_90d"]),
            "return_365d": float(latest_row["return_365d"]),
            "drawdown_from_ath_pct": float(latest_row["drawdown_from_ath_pct"]),
            "drawdown_30d_pct": float(latest_row["drawdown_30d_pct"]),
            "volatility_30d_pct": float(latest_row["volatility_30d_pct"]),
        }

        state.add_log("technical_agent")
        state.technical = run_technical_agent(df)

        state.add_log("ml_predictor")
        state.ml = predict_latest(df)

        state.add_log("regime_tool")
        state.regime = detect_regime(df)

        state.add_log("similarity_tool")
        state.similarity = find_similar_periods(
            df,
            top_k=SIMILARITY_TOP_K,
            exclude_recent_days=SIMILARITY_EXCLUDE_RECENT_DAYS,
        )

        state.add_log("cycle_tool")
        state.cycle = analyze_cycle(df)
        state.cycle["agent_view"] = run_cycle_agent(state.cycle)

        # 3) V2 core decision scores
        state.add_log("entry_engine")
        state.entry = score_entry(
            technical=state.technical,
            ml=state.ml,
            regime=state.regime,
            similarity=state.similarity,
        )

        state.add_log("exit_engine")
        state.exit = score_exit(state.latest, state.cycle)

        state.add_log("confidence_gate")
        state.gate = evaluate_confidence_gate(
            technical=state.technical,
            ml=state.ml,
            regime=state.regime,
            similarity=state.similarity,
            entry=state.entry,
            exit_signal=state.exit,
        )

        # 4) V3 Planner -> specialist routing -> retrieval/search -> synthesis
        state.add_log("planner_agent")
        state.plan = make_research_plan(state.question)

        state.add_log("specialist_research")
        state.experts, state.research = run_research(
            question=state.question,
            plan=state.plan,
            state=state,
            source=("demo" if injected_market_df and source == "live" else source),
        )
        state.evidence = collect_evidence(state.experts)

        state.add_log("research_engine")
        state.research_adjustment = apply_research_adjustment(state.entry, state.exit, state.research)

        # Research disagreement forces deeper review without letting research dominate scores.
        core_bias = (float(state.entry.get("score", 50)) - 50) * 2
        research_bias = float(state.research.get("score", 0))
        if state.gate and abs(core_bias - research_bias) >= 45:
            state.gate.route = "deep_analysis"
            state.gate.confidence = max(0.35, state.gate.confidence - 0.12)
            state.gate.reasons.append("Core engine and autonomous research disagree materially")

        # 5) Risk / decision / critic
        state.add_log("risk_agent")
        state.risk = run_risk_agent(state)

        state.add_log("decision_agent")
        decision = make_decision(state)
        state.draft_decision = decision

        if state.gate and state.gate.route == "deep_analysis":
            for iteration in range(MAX_CRITIC_ITERATIONS):
                state.iteration = iteration + 1
                state.add_log(f"critic_agent_{state.iteration}")
                critique = review_decision(state, decision)
                state.critiques.append(critique)
                if critique.passed:
                    break
                state.add_log(f"decision_revision_{state.iteration}")
                decision = revise_decision(state, decision, critique)

        state.add_log("position_engine")
        decision = apply_position_plan(
            decision,
            entry_score=float(state.research_adjustment.get("adjusted_entry_score", state.entry.get("score", 50))),
            exit_score=float(state.research_adjustment.get("adjusted_exit_score", state.exit.get("score", 0))),
        )
        state.final_decision = decision

        state.add_log("explanation_agent")
        state.explanation = explain_for_user(state)
        return state
