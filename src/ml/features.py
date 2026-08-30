import pandas as pd


FEATURES = [
    "rsi14",
    "ma20_gap_pct",
    "ma20_slope_5d",
    "ma200_gap_pct",
    "ma200_slope_20d",
    "volume_ratio",
    "return_3d",
    "return_7d",
]

MODEL_FEATURE_NAMES = [
    "rsi14",
    "ma20_gap_pct",
    "ma20_slope_5d",
    "ma200_gap_pct",
    "ma200_slope_20d",
    "volume_ratio",
    "return_3d_now",
    "return_7d_now",
]


def make_supervised_dataset(df: pd.DataFrame, horizon_days: int = 30) -> pd.DataFrame:
    work = df.copy().sort_values("date").reset_index(drop=True)

    work["future_return_30d"] = (
        work["close"].shift(-horizon_days) / work["close"] - 1
    ) * 100

    work = work.dropna(subset=FEATURES + ["future_return_30d"]).copy()
    work["target_up_30d"] = (work["future_return_30d"] > 0).astype(int)

    dataset = work[
        ["date", "close"] + FEATURES + ["future_return_30d", "target_up_30d"]
    ].copy()

    dataset = dataset.rename(
        columns={
            "return_3d": "return_3d_now",
            "return_7d": "return_7d_now",
        }
    )

    return dataset.reset_index(drop=True)


def latest_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    latest = df.dropna(subset=FEATURES).iloc[-1]

    return pd.DataFrame(
        [
            {
                "rsi14": latest["rsi14"],
                "ma20_gap_pct": latest["ma20_gap_pct"],
                "ma20_slope_5d": latest["ma20_slope_5d"],
                "ma200_gap_pct": latest["ma200_gap_pct"],
                "ma200_slope_20d": latest["ma200_slope_20d"],
                "volume_ratio": latest["volume_ratio"],
                "return_3d_now": latest["return_3d"],
                "return_7d_now": latest["return_7d"],
            }
        ],
        columns=MODEL_FEATURE_NAMES,
    )
