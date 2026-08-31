from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.engines.v5.forecast_engine import HORIZON_DAYS, _empirical_forecast
from src.tools.indicators import add_indicators


@dataclass
class ForecastObservation:
    horizon: str
    as_of: str
    probability_up_pct: float
    expected_return_pct: float
    q10_return_pct: float
    q90_return_pct: float
    confidence: float
    realized_return_pct: float

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _safe_mean(values: list[float]) -> float | None:
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return round(float(np.mean(vals)), 4) if vals else None


def _candidate_indices(n: int, days: int, max_points: int, min_history: int = 620) -> list[int]:
    last = n - days - 1
    if last <= min_history:
        return []
    pool = np.arange(min_history, last + 1)
    if len(pool) <= max_points:
        return [int(x) for x in pool]
    selected = np.linspace(pool[0], pool[-1], num=max_points, dtype=int)
    return sorted(set(int(x) for x in selected))


def validate_forecasts_walkforward(raw_df: pd.DataFrame, *, horizons: tuple[str, ...] = ("TODAY", "1W", "1M", "1Y"), max_points_per_horizon: int = 24) -> dict:
    """Walk-forward evaluation with strict truncation at every forecast timestamp.

    Each forecast only receives rows available at the historical as-of timestamp. Realized
    returns are read from the untouched full dataset afterward. This validates the numerical
    forecast layer; the full multi-agent allocation is intentionally tracked prospectively
    because historical derivatives/macro/news snapshots are not reconstructed here.
    """
    df = add_indicators(raw_df.copy()).sort_values("date").reset_index(drop=True)
    observations: list[ForecastObservation] = []
    skipped: dict[str, int] = {}

    for horizon in horizons:
        days = HORIZON_DAYS[horizon]
        skipped[horizon] = 0
        for idx in _candidate_indices(len(df), days, max_points_per_horizon):
            history = df.iloc[: idx + 1].copy()
            forecast = _empirical_forecast(history, days)
            if not forecast.get("available"):
                skipped[horizon] += 1
                continue
            p0 = float(df.iloc[idx]["close"])
            p1 = float(df.iloc[idx + days]["close"])
            realized = (p1 / p0 - 1.0) * 100.0
            observations.append(ForecastObservation(
                horizon=horizon,
                as_of=str(pd.Timestamp(df.iloc[idx]["date"])),
                probability_up_pct=float(forecast["probability_up_pct"]),
                expected_return_pct=float(forecast["expected_return_pct"]),
                q10_return_pct=float(forecast["q10_return_pct"]),
                q90_return_pct=float(forecast["q90_return_pct"]),
                confidence=float(forecast["confidence"]),
                realized_return_pct=realized,
            ))

    by_horizon: dict[str, dict] = {}
    for horizon in horizons:
        rows = [x for x in observations if x.horizon == horizon]
        if not rows:
            by_horizon[horizon] = {"samples": 0, "skipped": skipped.get(horizon, 0)}
            continue
        briers = []
        dir_hits = []
        abs_errors = []
        coverages = []
        confidences = []
        for x in rows:
            p = x.probability_up_pct / 100.0
            y = 1.0 if x.realized_return_pct > 0 else 0.0
            briers.append((p - y) ** 2)
            dir_hits.append(1.0 if (p >= 0.5) == (y == 1.0) else 0.0)
            abs_errors.append(abs(x.expected_return_pct - x.realized_return_pct))
            coverages.append(1.0 if x.q10_return_pct <= x.realized_return_pct <= x.q90_return_pct else 0.0)
            confidences.append(x.confidence)
        by_horizon[horizon] = {
            "samples": len(rows),
            "skipped": skipped.get(horizon, 0),
            "direction_accuracy": _safe_mean(dir_hits),
            "mean_brier": _safe_mean(briers),
            "mean_absolute_return_error_pct": _safe_mean(abs_errors),
            "q10_q90_coverage": _safe_mean(coverages),
            "mean_confidence": _safe_mean(confidences),
        }

    return {
        "validation": "strict_walkforward_forecast_layer",
        "lookahead_guard": "each historical forecast receives only rows at or before its as-of timestamp",
        "scope": "numerical forecast distributions only; full V5 council/risk allocation requires prospective live track record",
        "rows": len(df),
        "by_horizon": by_horizon,
        "observations": [x.to_dict() for x in observations],
    }
