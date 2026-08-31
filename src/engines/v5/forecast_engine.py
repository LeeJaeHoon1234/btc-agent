from __future__ import annotations

import math
from statistics import NormalDist
from typing import Iterable

import numpy as np
import pandas as pd

HORIZON_DAYS = {"TODAY": 1, "1W": 7, "1M": 30, "1Y": 365}
FEATURES = [
    "rsi14", "ma20_gap_pct", "ma20_slope_5d", "ma50_gap_pct",
    "ma200_gap_pct", "ma200_slope_20d", "volume_ratio", "return_7d",
    "return_30d", "volatility_30d_pct", "drawdown_from_ath_pct",
]


def _f(value, default=None):
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    v = values[order]
    w = weights[order]
    cdf = np.cumsum(w)
    if cdf[-1] <= 0:
        return float(np.quantile(v, q))
    return float(np.interp(q * cdf[-1], cdf, v))


def _empirical_forecast(df: pd.DataFrame, days: int) -> dict:
    work = df.copy().sort_values("date").reset_index(drop=True)
    cols = [x for x in FEATURES if x in work.columns]
    if len(cols) < 6:
        return {"available": False, "reason": "insufficient_feature_columns", "method": "historical_neighbors"}

    target = f"_future_return_{days}d"
    work[target] = (work["close"].shift(-days) / work["close"] - 1.0) * 100.0
    current_rows = work.dropna(subset=cols)
    if current_rows.empty:
        return {"available": False, "reason": "no_current_feature_row", "method": "historical_neighbors"}
    current = current_rows.iloc[-1]
    current_date = pd.Timestamp(current["date"])
    exclude_days = max(90, days + 14)
    candidates = work[(pd.to_datetime(work["date"]) < current_date - pd.Timedelta(days=exclude_days))].dropna(subset=cols + [target]).copy()
    if len(candidates) < 120:
        return {"available": False, "reason": "insufficient_history", "sample_count": int(len(candidates)), "method": "historical_neighbors"}

    matrix = candidates[cols].astype(float)
    means = matrix.mean()
    stds = matrix.std(ddof=0).replace(0, 1.0)
    z = (matrix - means) / stds
    current_z = (current[cols].astype(float) - means) / stds
    distances = np.sqrt(((z - current_z) ** 2).mean(axis=1).to_numpy(dtype=float))
    candidates["_distance"] = distances

    k = min(80, max(35, int(np.sqrt(len(candidates)) * 1.6)))
    nearest = candidates.nsmallest(k, "_distance").copy()
    vals = nearest[target].to_numpy(dtype=float)
    dists = nearest["_distance"].to_numpy(dtype=float)
    scale = float(np.median(dists)) or 1.0
    weights = np.exp(-dists / max(scale, 1e-6))
    weights = weights / weights.sum()

    mean = float(np.sum(vals * weights))
    median = _weighted_quantile(vals, weights, 0.50)
    q10 = _weighted_quantile(vals, weights, 0.10)
    q25 = _weighted_quantile(vals, weights, 0.25)
    q75 = _weighted_quantile(vals, weights, 0.75)
    q90 = _weighted_quantile(vals, weights, 0.90)
    raw_p_up = float(np.sum(weights[vals > 0]) * 100.0)
    p_gt5 = float(np.sum(weights[vals > 5]) * 100.0)
    p_lt5 = float(np.sum(weights[vals < -5]) * 100.0)
    dispersion = float(np.sqrt(np.sum(weights * (vals - mean) ** 2)))
    avg_distance = float(np.sum(weights * dists))
    similarity_quality = 1.0 / (1.0 + avg_distance)
    effective_n = float(1.0 / np.sum(weights ** 2))
    sample_quality = min(1.0, effective_n / 45.0)
    # Shrink extreme directional probabilities toward 50% when the effective analog
    # sample is small or the horizon is long. This prevents 0/100% looking certain.
    prior_n = {1: 8.0, 7: 12.0, 30: 18.0, 365: 45.0}.get(days, 18.0)
    p_up = ((raw_p_up / 100.0) * effective_n + 0.50 * prior_n) / (effective_n + prior_n) * 100.0
    direction_consensus = min(1.0, abs(p_up - 50.0) / 35.0)
    signal_to_noise = min(1.0, abs(mean) / max(1.0, dispersion * 0.55))
    horizon_penalty = {1: 0.00, 7: 0.03, 30: 0.08, 365: 0.20}.get(days, 0.08)
    confidence = 0.24 + 0.22 * similarity_quality + 0.18 * sample_quality + 0.20 * direction_consensus + 0.16 * signal_to_noise - horizon_penalty
    confidence_cap = {1: 0.76, 7: 0.70, 30: 0.64, 365: 0.55}.get(days, 0.64)
    confidence = float(np.clip(confidence, 0.25, confidence_cap))

    return {
        "available": True,
        "window_days": days,
        "expected_return_pct": round(mean, 3),
        "median_return_pct": round(median, 3),
        "q10_return_pct": round(q10, 3),
        "q25_return_pct": round(q25, 3),
        "q75_return_pct": round(q75, 3),
        "q90_return_pct": round(q90, 3),
        "probability_up_pct": round(p_up, 2),
        "raw_probability_up_pct": round(raw_p_up, 2),
        "probability_calibration": "effective_sample_bayesian_shrinkage_to_50pct",
        "probability_gt_5pct": round(p_gt5, 2),
        "probability_lt_minus_5pct": round(p_lt5, 2),
        "dispersion_pct": round(dispersion, 3),
        "confidence": round(confidence, 3),
        "sample_count": int(len(nearest)),
        "effective_sample_size": round(effective_n, 2),
        "avg_neighbor_distance": round(avg_distance, 4),
        "method": "distance_weighted_historical_neighbors",
        "calibration_status": "probability_shrunk; interval_requires_walkforward_and_live_calibration",
        "feature_count": len(cols),
    }


def _intraday_forecast(live: dict, daily_df: pd.DataFrame) -> dict:
    metrics = (live or {}).get("metrics") or {}
    r15 = _f(metrics.get("return_15m_pct"), 0.0)
    r1h = _f(metrics.get("return_1h_pct"), 0.0)
    r4h = _f(metrics.get("return_4h_pct"), 0.0)
    vwap = _f(metrics.get("vwap_gap_pct"), 0.0)
    imbalance = _f(metrics.get("orderbook_imbalance"), 0.0)
    taker = _f(metrics.get("spot_taker_buy_sell_ratio"), 1.0)
    atr = _f(metrics.get("atr14_pct"))

    # Deliberately damped: current momentum informs the next few hours but is not projected 1:1.
    mean = 0.18 * r15 + 0.22 * r1h + 0.08 * r4h - 0.06 * vwap
    mean += 0.18 * float(np.clip(imbalance, -0.5, 0.5))
    mean += 0.12 * float(np.clip((taker - 1.0), -0.5, 0.5))

    daily_vol = None
    if "volatility_30d_pct" in daily_df.columns:
        rows = daily_df.dropna(subset=["volatility_30d_pct"])
        if not rows.empty:
            daily_vol = float(rows.iloc[-1]["volatility_30d_pct"]) / math.sqrt(365)
    sigma = max(0.45, (atr or 0.0) * 1.8, (daily_vol or 0.0) * math.sqrt(4 / 24))
    sigma = min(sigma, 8.0)
    nd = NormalDist(mu=mean, sigma=sigma)
    q10, q90 = nd.inv_cdf(0.10), nd.inv_cdf(0.90)
    p_up = (1.0 - nd.cdf(0.0)) * 100.0
    return {
        "available": bool((live or {}).get("available")),
        "window_hours": 4,
        "expected_return_pct": round(mean, 3),
        "median_return_pct": round(mean, 3),
        "q10_return_pct": round(q10, 3),
        "q25_return_pct": round(nd.inv_cdf(0.25), 3),
        "q75_return_pct": round(nd.inv_cdf(0.75), 3),
        "q90_return_pct": round(q90, 3),
        "probability_up_pct": round(p_up, 2),
        "probability_gt_5pct": round((1.0 - nd.cdf(5.0)) * 100.0, 2),
        "probability_lt_minus_5pct": round(nd.cdf(-5.0) * 100.0, 2),
        "dispersion_pct": round(sigma, 3),
        "confidence": round(float(np.clip(0.38 + 0.08 * sum(x is not None for x in [r15, r1h, r4h, atr]), 0.35, 0.66)), 3),
        "sample_count": None,
        "method": "damped_intraday_state_distribution",
        "calibration_status": "heuristic_state_distribution_pending_live_calibration",
        "note": "NOW is a short-horizon state distribution, not a trained price target model.",
    }


def build_forecast_distributions(df: pd.DataFrame, live: dict | None = None) -> dict[str, dict]:
    out = {"NOW": _intraday_forecast(live or {}, df)}
    for horizon, days in HORIZON_DAYS.items():
        out[horizon] = _empirical_forecast(df, days)
    return out
