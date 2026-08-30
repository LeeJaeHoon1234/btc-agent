from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class GateResult:
    route: str
    confidence: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Decision:
    action: str
    confidence: float
    thesis: str
    reasons: list[str] = field(default_factory=list)
    invalidation: list[str] = field(default_factory=list)
    action_size_pct: float = 0.0
    source: str = "rule"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Critique:
    passed: bool
    severity: str
    issues: list[str] = field(default_factory=list)
    revision_instructions: list[str] = field(default_factory=list)
    source: str = "rule"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
