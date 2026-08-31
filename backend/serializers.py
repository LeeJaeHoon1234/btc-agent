from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def _clean(value: Any) -> Any:
    """Convert agent/Pandas/Numpy values into strict JSON-safe primitives."""
    if value is None:
        return None

    if is_dataclass(value):
        return _clean(asdict(value))

    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_clean(v) for v in value]

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None

    if isinstance(value, (np.bool_,)):
        return bool(value)

    return value


def serialize_state(state, series_points: int = 120) -> dict[str, Any]:
    decision = state.final_decision
    gate = state.gate

    series: list[dict[str, Any]] = []
    if state.market_df is not None and not state.market_df.empty:
        columns = [c for c in ["date", "close", "volume", "ma20", "ma200"] if c in state.market_df]
        recent = state.market_df[columns].tail(series_points)
        series = [_clean(row) for row in recent.to_dict(orient="records")]

    payload = {
        "latest": state.latest,
        "technical": state.technical,
        "ml": state.ml,
        "regime": state.regime,
        "similarity": state.similarity,
        "cycle": state.cycle,
        "entry": state.entry,
        "exit": state.exit,
        "risk": state.risk,
        "gate": gate.to_dict() if gate else None,
        "draft_decision": state.draft_decision.to_dict() if state.draft_decision else None,
        "final_decision": decision.to_dict() if decision else None,
        "explanation": state.explanation,
        "question": state.question,
        "plan": state.plan,
        "experts": state.experts,
        "research": state.research,
        "research_adjustment": state.research_adjustment,
        "evidence": state.evidence,
        "live": state.live,
        "events": state.events,
        "external": state.external,
        "data_health": state.data_health,
        "signals": state.signals,
        "horizons": state.horizons,
        "autonomy": state.autonomy,
        "v4_critic": state.v4_critic,
        "user_view": state.user_view,
        "critiques": [item.to_dict() for item in state.critiques],
        "iteration": state.iteration,
        "logs": state.logs,
        "series": series,
    }
    return _clean(payload)
