from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "rsi14", "ma20_gap_pct", "ma20_slope_5d", "ma200_gap_pct",
    "ma200_slope_20d", "volume_ratio", "return_7d", "return_30d",
    "drawdown_30d_pct", "volatility_30d_pct",
]


def retrieve_historical_cases(df: pd.DataFrame, top_k: int = 5, exclude_recent_days: int = 90) -> dict:
    work = df.copy()
    work["forward_7d"] = work["close"].shift(-7) / work["close"] - 1
    work["forward_30d"] = work["close"].shift(-30) / work["close"] - 1
    valid = work.dropna(subset=FEATURES + ["forward_7d", "forward_30d"]).copy()
    if len(valid) < max(150, exclude_recent_days + top_k):
        return {"available": False, "cases": [], "message": "Not enough history for retrieval."}

    current = work.dropna(subset=FEATURES).iloc[-1]
    cutoff_index = max(0, len(valid) - exclude_recent_days)
    candidates = valid.iloc[:cutoff_index].copy()
    if len(candidates) < top_k:
        return {"available": False, "cases": [], "message": "Not enough non-recent historical cases."}

    scaler = StandardScaler()
    x = scaler.fit_transform(candidates[FEATURES])
    q = scaler.transform(pd.DataFrame([current[FEATURES].to_dict()]))[0]
    distances = np.sqrt(((x - q) ** 2).mean(axis=1))
    candidates["distance"] = distances
    top = candidates.nsmallest(top_k, "distance")

    cases = []
    for _, row in top.iterrows():
        cases.append({
            "date": str(row["date"]),
            "close": float(row["close"]),
            "distance": float(row["distance"]),
            "forward_7d_pct": float(row["forward_7d"] * 100),
            "forward_30d_pct": float(row["forward_30d"] * 100),
            "rsi14": float(row["rsi14"]),
            "ma200_gap_pct": float(row["ma200_gap_pct"]),
        })

    f7 = [c["forward_7d_pct"] for c in cases]
    f30 = [c["forward_30d_pct"] for c in cases]
    return {
        "available": True,
        "cases": cases,
        "median_forward_7d_pct": float(np.median(f7)),
        "median_forward_30d_pct": float(np.median(f30)),
        "dispersion_30d_pct": float(np.std(f30)),
        "method": "standardized nearest-neighbor historical retrieval",
    }
