from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.core.schemas import Critique, Decision, GateResult


@dataclass
class AgentState:
    market_df: pd.DataFrame | None = None
    latest: dict[str, Any] = field(default_factory=dict)

    technical: dict[str, Any] = field(default_factory=dict)
    ml: dict[str, Any] = field(default_factory=dict)
    regime: dict[str, Any] = field(default_factory=dict)
    similarity: dict[str, Any] = field(default_factory=dict)
    cycle: dict[str, Any] = field(default_factory=dict)

    entry: dict[str, Any] = field(default_factory=dict)
    exit: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)

    gate: GateResult | None = None
    draft_decision: Decision | None = None
    critiques: list[Critique] = field(default_factory=list)
    final_decision: Decision | None = None
    explanation: dict[str, Any] = field(default_factory=dict)

    # V3 research layer kept for backward compatibility / advanced inspection.
    question: str = ""
    plan: dict[str, Any] = field(default_factory=dict)
    experts: dict[str, Any] = field(default_factory=dict)
    research: dict[str, Any] = field(default_factory=dict)
    research_adjustment: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    # V4 multi-speed market intelligence.
    live: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    external: dict[str, Any] = field(default_factory=dict)
    data_health: dict[str, Any] = field(default_factory=dict)
    signals: list[dict[str, Any]] = field(default_factory=list)
    horizons: dict[str, Any] = field(default_factory=dict)
    autonomy: dict[str, Any] = field(default_factory=dict)
    v4_critic: dict[str, Any] = field(default_factory=dict)
    user_view: dict[str, Any] = field(default_factory=dict)

    iteration: int = 0
    logs: list[str] = field(default_factory=list)

    def add_log(self, message: str) -> None:
        self.logs.append(message)

    def compact_context(self) -> dict[str, Any]:
        """Pass compact facts to LLMs instead of whole DataFrames."""
        return {
            "latest": self.latest,
            "live": self.live,
            "events": self.events,
            "technical": self.technical,
            "ml": self.ml,
            "regime": self.regime,
            "similarity": self.similarity,
            "cycle": self.cycle,
            "entry": self.entry,
            "exit": self.exit,
            "risk": self.risk,
            "question": self.question,
            "plan": self.plan,
            "experts": self.experts,
            "external": self.external,
            "data_health": self.data_health,
            "research": self.research,
            "research_adjustment": self.research_adjustment,
            "gate": self.gate.to_dict() if self.gate else None,
        }
