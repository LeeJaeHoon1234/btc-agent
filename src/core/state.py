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

    # V3 autonomous research layer
    question: str = ""
    plan: dict[str, Any] = field(default_factory=dict)
    experts: dict[str, Any] = field(default_factory=dict)
    research: dict[str, Any] = field(default_factory=dict)
    research_adjustment: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    iteration: int = 0
    logs: list[str] = field(default_factory=list)

    def add_log(self, message: str) -> None:
        self.logs.append(message)

    def compact_context(self) -> dict[str, Any]:
        """LLM에 DataFrame 전체 대신 필요한 상태만 전달한다."""
        return {
            "latest": self.latest,
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
            "research": self.research,
            "research_adjustment": self.research_adjustment,
            "gate": self.gate.to_dict() if self.gate else None,
        }
