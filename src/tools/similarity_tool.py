import numpy as np
import pandas as pd


SIMILARITY_FEATURES = [
    "rsi14",
    "ma20_gap_pct",
    "ma20_slope_5d",
    "ma200_gap_pct",
    "ma200_slope_20d",
    "volume_ratio",
    "return_3d",
    "return_7d",
]


def find_similar_periods(
    df: pd.DataFrame,
    top_k: int = 5,
    exclude_recent_days: int = 90,
    forward_days: int = 30,
) -> dict:
    work = df.copy().sort_values("date").reset_index(drop=True)
    work["future_return_30d"] = (
        work["close"].shift(-forward_days) / work["close"] - 1
    ) * 100

    valid = work.dropna(subset=SIMILARITY_FEATURES + ["future_return_30d"]).copy()
    if len(valid) < 200:
        return {
            "available": False,
            "matches": [],
            "message": "유사구간 검색에 필요한 과거 데이터가 부족합니다.",
        }

    current = work.dropna(subset=SIMILARITY_FEATURES).iloc[-1]
    cutoff_date = current["date"] - pd.Timedelta(days=exclude_recent_days)
    candidates = valid[valid["date"] < cutoff_date].copy()

    if candidates.empty:
        return {
            "available": False,
            "matches": [],
            "message": "최근 구간 제외 후 비교 가능한 데이터가 없습니다.",
        }

    feature_matrix = candidates[SIMILARITY_FEATURES].astype(float)
    current_vector = current[SIMILARITY_FEATURES].astype(float)

    means = feature_matrix.mean()
    stds = feature_matrix.std().replace(0, 1)

    candidate_z = (feature_matrix - means) / stds
    current_z = (current_vector - means) / stds

    squared_distance = ((candidate_z - current_z) ** 2).mean(axis=1).astype(float)
    distance = np.sqrt(squared_distance.to_numpy(dtype=float))
    candidates["distance"] = distance

    matches = candidates.nsmallest(top_k, "distance")

    output = []
    for _, row in matches.iterrows():
        output.append(
            {
                "date": str(pd.Timestamp(row["date"]).date()),
                "close": float(row["close"]),
                "distance": float(row["distance"]),
                "future_return_30d": float(row["future_return_30d"]),
            }
        )

    avg_return = float(matches["future_return_30d"].mean())
    up_rate = float((matches["future_return_30d"] > 0).mean() * 100)
    dispersion = float(matches["future_return_30d"].std(ddof=0))

    return {
        "available": True,
        "matches": output,
        "avg_forward_return_30d": avg_return,
        "up_rate_30d": up_rate,
        "dispersion_30d": dispersion,
    }
