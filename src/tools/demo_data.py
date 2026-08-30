"""Deterministic offline candle generator for smoke tests and demos.

Production analysis continues to use Upbit. This module exists so the complete
agent workflow and web UI can be exercised without an external network.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_demo_market_data(days: int = 1100, seed: int = 42) -> pd.DataFrame:
    if days < 450:
        raise ValueError("demo data needs at least 450 days for MA350/return_365d")

    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days, freq="D")
    t = np.arange(days, dtype=float)

    # Gentle long-term drift + market cycles + stochastic daily movement.
    daily_log_return = (
        0.00055
        + 0.0015 * np.sin(t / 37.0)
        + 0.0010 * np.sin(t / 113.0)
        + rng.normal(0.0, 0.018, days)
    )
    close = 45_000_000.0 * np.exp(np.cumsum(daily_log_return))
    open_ = close * (1 + rng.normal(0.0, 0.0035, days))
    high = np.maximum(open_, close) * (1 + rng.uniform(0.001, 0.022, days))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.001, 0.022, days))
    volume = rng.lognormal(mean=3.8, sigma=0.38, size=days)

    return pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )
